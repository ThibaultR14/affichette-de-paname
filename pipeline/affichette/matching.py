"""Screening title -> TMDB id, with the strategy chosen by spike #1 (docs/spikes/01-sources.md).

Resolution order, first answer wins:
  1. `pipeline/manual_overrides.csv` (normalized title + cinema; empty cinema = all cinemas);
  2. the TMDB id given by the source (`tmdb_hint`, SCARE);
  3. the `title_matches` cache (found: 30 days, not found: 7 days);
  4. TMDB search (fr-FR): director first, then title alone, then the director's filmography;
  5. otherwise no match (`tmdb_id = None`), listed in the report.

Manual check (from `pipeline/`, reads the repo's `.env`, writes nothing):
    uv run python -m affichette.matching "EVA" --director "LOSEY Joseph"
"""

from __future__ import annotations

import argparse
import csv
import html
import logging
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Protocol

from affichette.normalize import normalize_title
from affichette.tmdb import release_year

log = logging.getLogger(__name__)

OVERRIDES_CSV = Path(__file__).resolve().parents[1] / "manual_overrides.csv"
REUSE_FOUND = timedelta(days=30)
REUSE_NOT_FOUND = timedelta(days=7)

METHODS = ("override", "source", "director", "title", "none")


@dataclass(frozen=True)
class Thresholds:
    """Tuned on the spike sample (220 SCARE titles), see docs/decisions.md."""

    min_title: float = 0.5  # candidates below are ignored
    director_title: float = 0.7  # title similarity needed when the director matches
    director_score: float = 0.75
    title_score: float = 0.9  # title alone (no director match)
    filmography_title: float = 0.8
    ambiguous_title: float = 0.95  # several results this close: homonyms, no guess
    director_name: float = 0.85  # spelling variants of a director's name word
    director_candidates: int = 5  # credits checked on the first N results
    candidates: int = 8


@dataclass(frozen=True)
class MatchQuery:
    raw_title: str
    cinema_id: str | None = None
    director_hint: str | None = None
    year_hint: int | None = None
    tmdb_hint: int | None = None
    event_label: str | None = None


@dataclass(frozen=True)
class Match:
    tmdb_id: int | None
    method: str  # one of METHODS
    score: float | None = None
    reason: str | None = None  # why there is no match: empty|no_result|ambiguous|low_score|…


class TmdbLike(Protocol):
    def search_movie(self, query: str, year: int | None = None) -> list[dict]: ...
    def search_person(self, name: str) -> list[dict]: ...
    def person_directing(self, person_id: int) -> list[dict]: ...
    def movie(self, tmdb_id: int) -> Any: ...  # Cached(data={..., "directors": [...]})


# --- Title cleaning (ported from spikes/tmdb_match_probe.py) ------------------------------------

_SEP = re.compile(r"\s[-–—·•|]\s")
_GENERIC = re.compile(
    r"^(?:s[ée]ances? sp[ée]ciales?|avant[- ]premi[eè]re|cin[ée][- ]?club|cin[ée]-concert|"
    r"projection|sofilm|soir[ée]e)\b",
    re.IGNORECASE,
)
_NOISE = [
    r"\[[^\]]*\]",  # [7/13]
    r"\((?:vo|vf|vost(?:fr)?|4k|35 ?mm|70 ?mm|version restaur[ée]e)[^)]*\)",
    r"\s[-–—·•|]\s.*$",  # "SABRINA · Ciné-club Billy Wilder"
    r"\s\+\s.*$",  # "+ débat", "+ rencontre"
    r"\b(?:en )?(?:4k|35 ?mm|70 ?mm)\b",
    r"\bversion restaur[ée]e\b",
    r"\bavant[- ]premi[eè]re\b\s*:?",
    r"^(?:s[ée]ance sp[ée]ciale|cin[ée][- ]club|ciné-concert|projection)\b[^:]*:\s*",
    r"\bvost?f?r?\b$",
    r"\b(?:lun|mar|mer|jeu|ven|sam|dim)\.?\s+\d{1,2}(?:\s+\w+)?\s*:",  # "Ven 20 :"
    r"^\s*\d{1,2}\s+(?:janv?|f[ée]vr?|mars|avr|mai|juin|juil|ao[uû]t|sept?|oct|nov|d[ée]c)\w*\.?\s*$",
]
# "de Louis Clichy": capitalized words only, so "de la ville" is not a director.
_NAME = r"[A-Z][a-zà-ÿ][\w'-]*(?:\s+[A-Z][a-zà-ÿ][\w'-]*)+"


def clean_title(raw: str) -> str:
    """Screening title -> film title to search ('SABRINA · Ciné-club [7/13]' -> 'Sabrina')."""
    t = html.unescape(raw).strip()
    parts = _SEP.split(t)
    if len(parts) > 1 and _GENERIC.match(parts[0]):
        # "Séance spéciale - UN BON PETIT SOLDAT", "SOFILM #2 · Miami Vice de Michael Mann"
        t = re.sub(rf"\s+de\s+{_NAME}$", "", parts[-1])
    for pattern in _NOISE:
        t = re.sub(pattern, " ", t, flags=re.IGNORECASE)
    t = re.sub(rf",\s+de\s+{_NAME}$", "", t)  # ", de Louis Clichy"
    t = " ".join(t.split()).strip(" :-–")
    return t.title() if t.isupper() else t


def director_hint(raw: str) -> str | None:
    """Director named inside the title: '… de Michael Mann', 'Ciné-club Billy Wilder'."""
    text = html.unescape(raw)
    m = re.search(rf"\bde ({_NAME})\s*$", text)
    if not m:
        m = re.search(r"cin[ée]-club ([A-Z][a-z][\w'-]+ [A-Z][a-z][\w'-]+)", text, re.IGNORECASE)
    return m.group(1) if m else None


def clean_director(raw: str) -> str:
    """'LOSEY Joseph' -> 'Joseph Losey'; first name only when several are listed."""
    first = re.split(r",|;| et | & ", raw)[0].strip()
    words = first.split()
    if len(words) >= 2 and words[0].isupper() and not words[-1].isupper():
        words = words[1:] + [words[0].title()]
    return " ".join(words)


def director_tokens(name: str | None) -> set[str]:
    """Name words of 3+ letters, every director listed ('Meike Fehre, Sabine Dully')."""
    return {w for w in normalize_title(name).split() if len(w) > 2}


def same_director(wanted: set[str], directors: set[str], min_ratio: float) -> bool:
    """One name word in common, spelling variants allowed ('mikhail' / 'mikheil')."""
    return any(
        w == d or SequenceMatcher(None, w, d).ratio() >= min_ratio
        for w in wanted
        for d in directors
    )


def title_score(query: str, cand: dict) -> float:
    """Best similarity between `query` and the French or original title (0..1)."""
    q = normalize_title(query)
    return max(
        SequenceMatcher(None, q, normalize_title(cand.get(k))).ratio()
        for k in ("title", "original_title")
    )


def title_only_score(similarity: float, rank: int, director_known: bool) -> float:
    """Score without a director match: favour TMDB's first result, distrust a wrong director."""
    return similarity * (0.95 if rank == 0 else 0.8) * (0.9 if director_known else 1.0)


def director_score(similarity: float) -> float:
    return 0.6 + 0.4 * similarity


def year_ok(cand: dict, year_hint: int | None) -> bool:
    """Release year within ±1 of the hint (unknown years pass)."""
    year = release_year(cand.get("release_date"))
    return year_hint is None or year is None or abs(year - year_hint) <= 1


# --- Overrides ----------------------------------------------------------------------------------


def load_overrides(path: Path = OVERRIDES_CSV) -> dict[tuple[str, str | None], int | None]:
    """`title,cinema_id,tmdb_id,note` -> {(normalized title, cinema or None): tmdb_id or None}.

    The title may be pasted raw: it is normalized here. Empty `tmdb_id` = "not a film".
    """
    overrides: dict[tuple[str, str | None], int | None] = {}
    if not path.exists():
        return overrides
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        missing = {"title", "cinema_id", "tmdb_id"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path.name} : colonnes manquantes {sorted(missing)}")
        for row in reader:
            line = reader.line_num
            title = (row["title"] or "").strip()
            if not title or title.startswith("#"):
                continue
            key = (normalize_title(title), (row["cinema_id"] or "").strip() or None)
            raw_id = (row["tmdb_id"] or "").strip()
            if raw_id and (not raw_id.isdigit() or int(raw_id) <= 0):
                raise ValueError(f"{path.name} ligne {line} : tmdb_id invalide {raw_id!r}")
            if key in overrides:
                raise ValueError(f"{path.name} ligne {line} : doublon {title!r}")
            overrides[key] = int(raw_id) if raw_id else None
    return overrides


# --- title_matches cache -----------------------------------------------------------------------

CacheKey = tuple[str, str | None, int | None]  # normalized raw title, cinema, year hint


@dataclass(frozen=True)
class CachedMatch:
    tmdb_id: int | None
    method: str
    score: float | None
    matched_at: datetime
    reason: str | None = None  # why a "none" failed (empty, no_result, ambiguous, low_score)


PAGE_SIZE = 1000  # Supabase `max_rows`: PostgREST never returns more per request


class TitleMatchStore:
    """In-memory `title_matches` (tests, dry runs). `DbTitleMatchStore` persists it."""

    def __init__(self, rows: dict[CacheKey, CachedMatch] | None = None):
        self.rows: dict[CacheKey, CachedMatch] = dict(rows or {})
        self.pending: dict[CacheKey, CachedMatch] = {}

    def get(self, key: CacheKey) -> CachedMatch | None:
        return self.rows.get(key)

    def put(self, key: CacheKey, match: Match, now: datetime) -> None:
        entry = CachedMatch(match.tmdb_id, match.method, match.score, now, match.reason)
        self.rows[key] = self.pending[key] = entry

    def pending_rows(self) -> list[dict[str, Any]]:
        return [
            {
                "normalized_title": title,
                "cinema_id": cinema_id,
                "year_hint": year,
                "tmdb_id": m.tmdb_id,
                "method": m.method,
                "score": None if m.score is None else round(m.score, 4),
                "matched_at": m.matched_at.isoformat(),
                "reason": m.reason,
            }
            for (title, cinema_id, year), m in self.pending.items()
        ]

    def flush(self) -> None:
        self.pending.clear()


class DbTitleMatchStore(TitleMatchStore):
    """`title_matches` in Supabase: one GET per cinema, one upsert at the end."""

    def __init__(self, db: Any):
        super().__init__()
        self.db = db
        self.loaded: set[str | None] = set()

    def load(self, cinema_id: str | None) -> None:
        if cinema_id in self.loaded:
            return
        offset = 0
        while True:
            rows = self.db.select(
                "title_matches",
                {
                    "select": (
                        "normalized_title,cinema_id,year_hint,tmdb_id,method,score,matched_at,reason"
                    ),
                    "cinema_id": f"eq.{cinema_id}" if cinema_id else "is.null",
                    "order": "id",
                    "limit": str(PAGE_SIZE),
                    "offset": str(offset),
                },
            )
            for r in rows:
                key = (r["normalized_title"], r["cinema_id"], r["year_hint"])
                self.rows[key] = CachedMatch(
                    r["tmdb_id"],
                    r["method"],
                    r["score"],
                    datetime.fromisoformat(r["matched_at"]),
                    r.get("reason"),
                )
            if len(rows) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
        self.loaded.add(cinema_id)

    def get(self, key: CacheKey) -> CachedMatch | None:
        self.load(key[1])
        return super().get(key)

    def flush(self) -> None:
        self.db.upsert(
            "title_matches", self.pending_rows(), on_conflict="normalized_title,cinema_id,year_hint"
        )
        super().flush()


# --- Report -------------------------------------------------------------------------------------


@dataclass
class MatchReport:
    """Per run: screenings per method, unmatched titles (events apart), title-only matches."""

    screenings: Counter[str] = field(default_factory=Counter)
    unmatched: dict[tuple[str | None, str], dict[str, Any]] = field(default_factory=dict)
    title_only: dict[tuple[str | None, str], dict[str, Any]] = field(default_factory=dict)

    def add(self, query: MatchQuery, match: Match) -> None:
        self.screenings[match.method] += 1
        key = (query.cinema_id, query.raw_title)
        if match.tmdb_id is None and match.reason == "override":
            return  # "not a film" on purpose (CSV): nothing to review
        if match.tmdb_id is None:
            director = query.director_hint or director_hint(query.raw_title)
            entry = self.unmatched.setdefault(
                key,
                {
                    "query": query,
                    "reason": match.reason,
                    "event": bool(query.event_label) and not director,
                    "n": 0,
                },
            )
            entry["n"] += 1
        elif match.method == "title":
            entry = self.title_only.setdefault(
                key, {"query": query, "tmdb_id": match.tmdb_id, "score": match.score, "n": 0}
            )
            entry["n"] += 1

    @property
    def total(self) -> int:
        return sum(self.screenings.values())

    def summary(self) -> str:
        matched = self.total - self.screenings["none"]
        lines = [
            f"correspondance TMDB : {matched}/{self.total} séance(s)"
            + "".join(f", {m} {self.screenings[m]}" for m in METHODS if self.screenings[m]),
        ]
        films = [e for e in self.unmatched.values() if not e["event"]]
        events = [e for e in self.unmatched.values() if e["event"]]
        for label, entries in (("films sans correspondance", films), ("événements", events)):
            if entries:
                lines.append(f"{label} ({len(entries)}) :")
                lines += [
                    f"  - [{e['query'].cinema_id or '?'}] {e['query'].raw_title}"
                    f" ({e['reason']}, {e['n']} séance(s))"
                    for e in sorted(entries, key=lambda e: (e["query"].cinema_id or "", -e["n"]))
                ]
        if self.title_only:
            lines.append(f"titre seul, à relire ({len(self.title_only)}) :")
            lines += [
                f"  - [{e['query'].cinema_id or '?'}] {e['query'].raw_title} → {e['tmdb_id']}"
                f" ({e['score']:.2f})"
                for e in self.title_only.values()
            ]
        return "\n".join(lines)


# --- Matcher ------------------------------------------------------------------------------------


class Matcher:
    def __init__(
        self,
        tmdb: TmdbLike,
        overrides: dict[tuple[str, str | None], int | None] | None = None,
        store: TitleMatchStore | None = None,
        thresholds: Thresholds = Thresholds(),
        now: datetime | None = None,
    ):
        self.tmdb = tmdb
        self.overrides = overrides if overrides is not None else load_overrides()
        self.store = store if store is not None else TitleMatchStore()
        self.t = thresholds
        self.now = now or datetime.now(UTC)
        self.report = MatchReport()
        self._memo: dict[MatchQuery, Match] = {}

    def match(self, query: MatchQuery) -> Match:
        """Resolve one screening and record it in `self.report`."""
        if query not in self._memo:
            self._memo[query] = self._resolve(query)
        result = self._memo[query]
        self.report.add(query, result)
        return result

    def _resolve(self, q: MatchQuery) -> Match:
        raw_key = normalize_title(q.raw_title)
        cleaned = clean_title(q.raw_title)
        clean_key = normalize_title(cleaned)
        for key in ((raw_key, q.cinema_id), (clean_key, q.cinema_id), (raw_key, None),
                    (clean_key, None)):  # fmt: skip
            if key in self.overrides:
                tmdb_id = self.overrides[key]
                return Match(tmdb_id, "override" if tmdb_id else "none", 1.0, "override")
        if q.tmdb_hint:
            return Match(int(q.tmdb_hint), "source", 1.0)

        cache_key: CacheKey = (raw_key, q.cinema_id, q.year_hint)
        cached = self.store.get(cache_key)
        if cached is not None:
            reuse = REUSE_FOUND if cached.tmdb_id else REUSE_NOT_FOUND
            if self.now - cached.matched_at < reuse:
                return Match(cached.tmdb_id, cached.method, cached.score, cached.reason)

        director = q.director_hint or director_hint(q.raw_title)
        result = self._search(cleaned, director, q.year_hint)
        self.store.put(cache_key, result, self.now)
        return result

    def _directors(self, tmdb_id: int) -> set[str]:
        data = self.tmdb.movie(tmdb_id).data or {}
        return {w for name in data.get("directors") or [] for w in director_tokens(name)}

    def _candidates(self, query: str, year: int | None) -> list[dict]:
        cands = [c for c in self.tmdb.search_movie(query) if year_ok(c, year)]
        if not cands and year:  # common title: the right film may be past the first page
            cands = [c for c in self.tmdb.search_movie(query, year) if year_ok(c, year)]
        return cands[: self.t.candidates]

    def _search(self, query: str, director: str | None, year: int | None) -> Match:
        t = self.t
        if len(normalize_title(query)) < 2:
            return Match(None, "none", 0.0, "empty")
        cands = self._candidates(query, year)
        wanted = director_tokens(director)
        if not cands and not wanted:
            return Match(None, "none", 0.0, "no_result")

        best_score, best_id, best_method = 0.0, None, "none"
        for rank, cand in enumerate(cands):
            sim = title_score(query, cand)
            if sim < t.min_title:
                continue
            if wanted and rank < t.director_candidates and sim >= t.director_title:
                if same_director(wanted, self._directors(cand["id"]), t.director_name):
                    score = director_score(sim)
                    if score > best_score:
                        best_score, best_id, best_method = score, cand["id"], "director"
                    continue
            score = title_only_score(sim, rank, bool(wanted))
            if score > best_score and best_method != "director":
                best_score, best_id, best_method = score, cand["id"], "title"

        if best_method != "director" and director and wanted:
            # Homonyms (Losey's "Eva") or no French title on TMDB: look in the filmography.
            for cand in self._filmography(clean_director(director)):
                sim = title_score(query, cand)
                if sim < t.filmography_title or not year_ok(cand, year):
                    continue
                if best_method != "director" or director_score(sim) > best_score:
                    best_score, best_id, best_method = director_score(sim), cand["id"], "director"

        if best_method == "title":
            close = [c for c in cands if title_score(query, c) >= t.ambiguous_title]
            if len(close) > 1:  # "Sabrina" 1954 or 1995: no blind guess
                return Match(None, "none", best_score, "ambiguous")
        threshold = t.director_score if best_method == "director" else t.title_score
        if best_id is None and not cands:
            return Match(None, "none", 0.0, "no_result")
        if best_id is None or best_score < threshold:
            return Match(None, "none", best_score, "low_score")
        return Match(int(best_id), best_method, best_score)

    def _filmography(self, director: str) -> list[dict]:
        people = [
            p
            for p in self.tmdb.search_person(director)
            if p.get("known_for_department") == "Directing"
        ]
        return self.tmdb.person_directing(people[0]["id"]) if people else []


# --- CLI ----------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    from dotenv import load_dotenv

    from affichette.tmdb import Tmdb, TmdbError

    parser = argparse.ArgumentParser(description="Essai de correspondance titre → TMDB.")
    parser.add_argument("title")
    parser.add_argument("--director")
    parser.add_argument("--year", type=int)
    parser.add_argument("--cinema")
    parser.add_argument("--hint", type=int, help="tmdb_id donné par la source")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    try:
        matcher = Matcher(Tmdb())
        query = MatchQuery(args.title, args.cinema, args.director, args.year, args.hint)
        result = matcher.match(query)
    except (TmdbError, ValueError) as exc:
        log.error("%s", exc)
        return 1
    print(f"titre nettoyé : {clean_title(args.title)!r}")
    print(result)
    print(matcher.report.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
