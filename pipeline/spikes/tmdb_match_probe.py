"""Spike #1 - throwaway probe of title -> TMDB matching on real screening titles.

Titles come from the SCARE open dataset (all of France, Paris first). The dataset's own
`_donnees_imdb.id` (a TMDB id despite the name) is used as a reference to measure agreement.

Strategy tested (docs/architecture.md):
  1. clean the screening title (event prefixes/suffixes, "[7/13]", "+ débat", "4K"...);
  2. TMDB search language=fr-FR (with year when known);
  3. score candidates: normalized title similarity (fr + original title) and director match
     through credits; accept above a confidence threshold, else no match.

Usage: uv run python spikes/tmdb_match_probe.py [--limit 200] [--offline-titles]
TMDB_READ_TOKEN is read from the environment or from Recsys' .env (never printed).
Not tested, not imported by the pipeline.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import random
import re
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(__file__).parent / "data"
CACHE = ROOT / "data" / "cache" / "spike_tmdb"
SCARE = "https://datacinesindes.fr/data-fair/api/v1/datasets/programmation-cinemas/lines"
TMDB = "https://api.themoviedb.org/3"
UA = {"User-Agent": "affichette-spike/0.1"}


# ---------------------------------------------------------------- titles


def fetch_titles() -> list[dict]:
    rows: list[dict] = []
    url: str | None = SCARE
    params: dict | None = {
        "size": 10000,
        "select": "filmtitle,filmdirector,cinenom,cinecp,_donnees_imdb.id,evenement",
    }
    while url:
        resp = requests.get(url, params=params, headers=UA, timeout=60)
        resp.raise_for_status()
        body = resp.json()
        rows.extend(body["results"])
        url, params = body.get("next"), None
    (DATA / "scare_titles.json").write_text(json.dumps(rows, ensure_ascii=False), "utf-8")
    return rows


def sample_titles(rows: list[dict], limit: int) -> list[dict]:
    seen: dict[str, dict] = {}
    for r in rows:
        title = (r.get("filmtitle") or "").strip()
        if title and title.casefold() not in seen:
            seen[title.casefold()] = r
    paris = [r for r in seen.values() if str(r.get("cinecp", "")).startswith("75")]
    others = [r for r in seen.values() if not str(r.get("cinecp", "")).startswith("75")]
    random.Random(1).shuffle(others)
    return (paris + others)[:limit]


# ---------------------------------------------------------------- normalization


def normalize(title: str | None) -> str:
    """Same rules as Recsys titles.py v2: casefold, NFKD, drop marks, keep letters/digits."""
    if not title:
        return ""
    t = unicodedata.normalize("NFKD", title.casefold())
    out = []
    for c in t:
        cat = unicodedata.category(c)[0]
        if cat == "M":
            continue
        out.append(c if cat in "LN" else " ")
    return " ".join("".join(out).split())


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
    # dates: "2 décembre", "Ven 20 :", "Sam 28 nov :"
    r"\b(?:lun|mar|mer|jeu|ven|sam|dim)\.?\s+\d{1,2}(?:\s+\w+)?\s*:",
    r"^\s*\d{1,2}\s+(?:janv?|f[ée]vr?|mars|avr|mai|juin|juil|ao[uû]t|sept?|oct|nov|d[ée]c)\w*\.?\s*$",
]


_GENERIC = re.compile(
    r"^(?:s[ée]ances? sp[ée]ciales?|avant[- ]premi[eè]re|cin[ée][- ]?club|cin[ée]-concert|"
    r"projection|sofilm|soir[ée]e)\b",
    re.IGNORECASE,
)
_SEP = re.compile(r"\s[-–—·•|]\s")


def clean_title(raw: str) -> str:
    t = html.unescape(raw).strip()
    parts = _SEP.split(t)
    # "Séance spéciale - UN BON PETIT SOLDAT", "Ciné-concert · Le Violon de Mr Chaplin"
    if len(parts) > 1 and _GENERIC.match(parts[0]):
        # "SOFILM CINÉ-CLUB #2 · Miami Vice de Michael Mann" (the director goes to director_hint)
        t = re.sub(r"\s+de\s+[A-Z][a-z][\w'-]*(?:\s+[A-Z][a-z][\w'-]*)+$", "", parts[-1])
    for pattern in _NOISE:
        t = re.sub(pattern, " ", t, flags=re.IGNORECASE)
    t = re.sub(r",\s+de\s+[A-Z][\w'-]+(?:\s+[A-Z][\w'-]+)+$", "", t)  # ", de Louis Clichy"
    t = " ".join(t.split()).strip(" :-–")
    return t if t.isupper() is False else t.title()


def director_hint(raw: str) -> str | None:
    """Director named inside the title: '... de Michael Mann', 'Ciné-club Billy Wilder'."""
    m = re.search(r"\bde ([A-Z][\w'-]+(?: [A-Z][\w'-]+)+)\s*$", html.unescape(raw))
    if not m:
        m = re.search(r"cin[ée]-club ([A-Z][a-z][\w'-]+ [A-Z][a-z][\w'-]+)", raw, re.IGNORECASE)
    return m.group(1) if m else None


def clean_director(raw: str) -> str:
    """'LOSEY Joseph' -> 'Joseph Losey'; first name only when several are listed."""
    first = re.split(r",|;| et | & ", raw)[0].strip()
    words = first.split()
    if len(words) >= 2 and words[0].isupper() and not words[-1].isupper():
        words = words[1:] + [words[0].title()]
    return " ".join(words)


def director_tokens(raw: str | None) -> set[str]:
    return {w for w in normalize(raw).split() if len(w) > 2}


# ---------------------------------------------------------------- TMDB client


class Tmdb:
    def __init__(self) -> None:
        load_dotenv(ROOT / ".env")
        load_dotenv(Path("C:/dev/Projet_recsys_movie/.env"))
        token = os.environ.get("TMDB_READ_TOKEN", "").strip()
        if not token:
            raise SystemExit("TMDB_READ_TOKEN manquant")
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"
        self.calls = 0
        CACHE.mkdir(parents=True, exist_ok=True)

    def _get(self, path: str, params: dict, cache_key: str) -> dict:
        file = CACHE / f"{cache_key}.json"
        if file.exists():
            return json.loads(file.read_text("utf-8"))
        for attempt in range(4):
            time.sleep(0.05)
            try:
                resp = self.session.get(TMDB + path, params=params, timeout=20)
            except requests.RequestException as e:  # its message holds the URL: never log it
                raise RuntimeError(f"TMDB {path.split('/')[1]}: {type(e).__name__}") from None
            self.calls += 1
            if resp.status_code == 429:
                time.sleep(2**attempt)
                continue
            if not resp.ok:  # never log the URL (project rule)
                raise RuntimeError(f"TMDB {path.split('/')[1]}: HTTP {resp.status_code}")
            data = resp.json()
            file.write_text(json.dumps(data, ensure_ascii=False), "utf-8")
            return data
        raise RuntimeError("TMDB: trop de 429")

    def search(self, query: str, year: int | None = None) -> list[dict]:
        params = {"query": query, "language": "fr-FR", "include_adult": "false"}
        if year:
            params["year"] = year
        key = "search_" + normalize(query).replace(" ", "_")[:80] + (f"_{year}" if year else "")
        return self._get("/search/movie", params, key).get("results", [])

    def directors(self, tmdb_id: int) -> set[str]:
        data = self._get(f"/movie/{tmdb_id}/credits", {}, f"credits_{tmdb_id}")
        names = [c["name"] for c in data.get("crew", []) if c.get("job") == "Director"]
        return {w for n in names for w in director_tokens(n)}

    def directed_by(self, director: str) -> list[dict]:
        """Films directed by the best 'Directing' person matching `director` (fallback)."""
        key = normalize(director).replace(" ", "_")[:60]
        people = self._get("/search/person", {"query": director}, f"person_{key}")
        people = [
            p for p in people.get("results", []) if p.get("known_for_department") == "Directing"
        ]
        if not people:
            return []
        pid = people[0]["id"]
        data = self._get(f"/person/{pid}/movie_credits", {"language": "fr-FR"}, f"pcred_{pid}")
        return [c for c in data.get("crew", []) if c.get("job") == "Director"]


# ---------------------------------------------------------------- matching


def title_score(query: str, cand: dict) -> float:
    q = normalize(query)
    return max(
        SequenceMatcher(None, q, normalize(cand.get(k))).ratio()
        for k in ("title", "original_title")
    )


def match(api: Tmdb, raw_title: str, director: str | None) -> tuple[int | None, str, float]:
    query = clean_title(raw_title)
    if len(normalize(query)) < 2:
        return None, "none:empty", 0.0
    cands = api.search(query)[:8]
    wanted = director_tokens(director)
    if not cands and not wanted:
        return None, "none:no_result", 0.0
    best: tuple[float, int | None, str] = (0.0, None, "none")
    for i, cand in enumerate(cands):
        ts = title_score(query, cand)
        if ts < 0.5:
            continue
        if wanted and i < 5:
            if ts >= 0.7 and wanted & api.directors(cand["id"]):
                score = 0.6 + 0.4 * ts
                if score > best[0]:
                    best = (score, cand["id"], "director")
                continue
        # no director info: title only, favour the first (most relevant) result
        score = ts * (0.95 if i == 0 else 0.8) * (0.9 if wanted else 1.0)
        if score > best[0]:
            best = (score, cand["id"], "title")
    if best[2] != "director" and director and wanted:
        # homonyms (Losey's "Eva") or titles TMDB lacks in French: look in the filmography
        for cand in api.directed_by(clean_director(director)):
            ts = title_score(query, cand)
            if ts >= 0.8 and 0.6 + 0.4 * ts > best[0]:
                best = (0.6 + 0.4 * ts, cand["id"], "director")
    if best[2] == "title":
        exact = [c for c in cands if title_score(query, c) >= 0.95]
        if len(exact) > 1:  # homonyms / remakes ("Sabrina" 1954 vs 1995): no blind guess
            return None, "none:ambiguous", best[0]
    score, tmdb_id, method = best
    threshold = 0.75 if method == "director" else 0.9
    if tmdb_id is None or score < threshold:
        return None, f"none:low_score({method})", score
    return tmdb_id, method, score


# ---------------------------------------------------------------- main


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--offline-titles", action="store_true")
    args = parser.parse_args()
    DATA.mkdir(exist_ok=True)
    cached = DATA / "scare_titles.json"
    rows = json.loads(cached.read_text("utf-8")) if args.offline_titles else fetch_titles()
    sample = sample_titles(rows, args.limit)
    api = Tmdb()

    out = []
    for r in sample:
        director = r.get("filmdirector") or director_hint(r["filmtitle"])
        tmdb_id, method, score = match(api, r["filmtitle"], director)
        ref = r.get("_donnees_imdb.id")
        out.append(
            {
                "raw_title": r["filmtitle"],
                "clean_title": clean_title(r["filmtitle"]),
                "director": director or "",
                "cinema": r.get("cinenom"),
                "paris": str(r.get("cinecp", "")).startswith("75"),
                "event": r.get("evenement") or "",
                "tmdb_id": tmdb_id or "",
                "method": method,
                "score": round(score, 3),
                "scare_tmdb_id": ref or "",
                "agree": "" if not (ref and tmdb_id) else str(int(ref) == tmdb_id),
            }
        )
    with (DATA / "tmdb_match_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(out[0]))
        writer.writeheader()
        writer.writerows(out)

    n = len(out)
    matched = [o for o in out if o["tmdb_id"]]
    with_ref = [o for o in out if o["scare_tmdb_id"]]
    both = [o for o in out if o["agree"]]
    agree = [o for o in both if o["agree"] == "True"]
    print(f"titres: {n} (Paris {sum(o['paris'] for o in out)}), appels TMDB: {api.calls}")
    print(f"correspondance auto: {len(matched)}/{n} = {len(matched) / n:.0%}")
    print(f"avec id SCARE: {len(with_ref)}/{n}; accord: {len(agree)}/{len(both)}")
    ref_only = [o for o in with_ref if not o["tmdb_id"]]
    print(f"id SCARE mais pas de match chez nous: {len(ref_only)}")
    extra = sum(1 for o in matched if not o["scare_tmdb_id"])
    print(f"match chez nous mais pas d'id SCARE: {extra}")


if __name__ == "__main__":
    main()
