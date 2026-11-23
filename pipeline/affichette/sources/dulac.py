"""Dulac cinemas API (Reflet Médicis): `GET /api/home-bootstrap?days=7` on dulaccinemas.com.

One call per run returns the 5 Dulac cinemas; seances are matched to `cinemas.source_ref` = the
cinema node id through `salles_by_id[salle_id].cinema_id`. See docs/spikes/01-sources.md.

Quirks of the response:
- `date` is UTC without a "Z" ("2026-11-24T19:00:00" for a 20:00 show in Paris);
- `year` is usually 0 and `release_date` is the French (re-)release date, so it is not used;
- the same show can appear twice (two seance ids, two film records, same room and time): the
  duplicates are merged on (salle, start) and the most complete film record is kept.
The key is the Dulac seance id: unlike the ticketing link, it is there from the start.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import requests

from affichette.normalize import normalize_format, normalize_version
from affichette.sources import Cinema, RawScreening, SourceError

log = logging.getLogger(__name__)

API = "https://www.dulaccinemas.com/api/home-bootstrap"
PARAMS = {"days": "7"}
USER_AGENT = "affichette-de-paname/0.1 (import quotidien, non commercial)"
TIMEOUT_S = 30


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def dulac_version(raw: str | None) -> str | None:
    """'VOST' -> 'VOSTFR', 'VF' -> 'VF', anything else through `normalize_version`."""
    text = (_text(raw) or "").upper()
    if text == "VOST":
        return "VOSTFR"
    return normalize_version(text)


def _positive_int(value: Any) -> int | None:
    return int(value) if isinstance(value, int | float) and value > 0 else None


def _starts_at(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def _format(seance: dict[str, Any], film: dict[str, Any]) -> str | None:
    candidates = [seance.get("format"), *(film.get("projection_formats") or [])]
    candidates += [film.get("title"), seance.get("info")]
    for raw in candidates:
        fmt = normalize_format(_text(raw))
        if fmt:
            return fmt
    return None


def _completeness(film: dict[str, Any], seance: dict[str, Any]) -> tuple[int, int]:
    """Used to pick between two records of the same show: most complete, then oldest id."""
    score = sum(bool(film.get(k)) for k in ("original_title", "directors", "release_date"))
    score += bool(_text(seance.get("booking_url")))
    seance_id = _text(seance.get("id")) or ""
    return score, -int(seance_id) if seance_id.isdigit() else 0


def parse_seance(
    seance: dict[str, Any], film: dict[str, Any], cinema_id: str
) -> RawScreening | None:
    """One Dulac seance -> RawScreening, or None (cancelled, no title, unreadable date)."""
    if seance.get("is_cancelled"):
        return None
    title = _text(film.get("title"))
    seance_id = _text(seance.get("id"))
    if not title or not seance_id:
        return None
    starts_at = _starts_at(_text(seance.get("date")))
    if starts_at is None:
        log.warning(
            "Dulac : horaire illisible %r (séance %s), ignorée", seance.get("date"), seance_id
        )
        return None
    booking_url = _text(seance.get("booking_url"))
    directors = [d for d in (film.get("directors") or []) if _text(d)]
    # `is_special` is also set for "first session" (opening day): only `type` marks an event.
    special = (seance.get("type") or "standard") != "standard"
    return RawScreening(
        source_key=f"dulac:{cinema_id}:{seance_id}",
        cinema_id=cinema_id,
        raw_title=title,
        starts_at=starts_at,
        version=dulac_version(seance.get("version")),
        format=_format(seance, film),
        booking_url=booking_url,
        runtime_hint=_positive_int(film.get("duration")),
        year_hint=_positive_int(film.get("year")),
        director_hint=", ".join(directors) or _text(film.get("director")),
        event_label=_text(seance.get("event_label")) if special else None,
    )


class DulacSource:
    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self._body: dict[str, Any] | None = None
        self._error: SourceError | None = None

    def body(self) -> dict[str, Any]:
        """The API response, downloaded once per run (a failure is remembered too)."""
        if self._error is not None:
            raise self._error
        if self._body is None:
            try:
                self._body = self._download()
            except SourceError as exc:
                self._error = exc
                raise
        return self._body

    def _download(self) -> dict[str, Any]:
        try:
            r = self.session.get(API, params=PARAMS, timeout=TIMEOUT_S)
        except requests.RequestException as exc:
            # str(exc) contains the URL: keep the type only.
            raise SourceError(f"Dulac injoignable ({type(exc).__name__})") from None
        if r.status_code != 200:
            raise SourceError(f"Dulac : HTTP {r.status_code}")
        try:
            body = r.json()
            seances = body["seances_week"]
            ok = (
                isinstance(seances, list)
                and isinstance(body.get("films_by_id"), dict)
                and isinstance(body.get("salles_by_id"), dict)
                and isinstance(body.get("cinemas_by_id"), dict)
            )
        except (ValueError, KeyError, TypeError):
            ok = False
        if not ok:
            raise SourceError("Dulac : réponse illisible")
        if (body.get("meta") or {}).get("truncated"):
            # Missing seances would be marked cancelled.
            raise SourceError("Dulac : réponse tronquée (seances_max atteint)")
        if not seances:
            raise SourceError("Dulac : aucune séance dans la réponse")
        return body

    def fetch(self, cinema: Cinema, start: datetime, end: datetime) -> list[RawScreening]:
        if not cinema.source_ref:
            raise SourceError(f"{cinema.id} : source_ref Dulac manquant")
        body = self.body()
        if cinema.source_ref not in body["cinemas_by_id"]:
            raise SourceError(f"{cinema.id} : salle absente de l'API Dulac ({cinema.source_ref!r})")
        salles = {
            salle_id
            for salle_id, salle in body["salles_by_id"].items()
            if isinstance(salle, dict) and str(salle.get("cinema_id")) == cinema.source_ref
        }
        if not salles:
            # Renamed field or renumbered rooms: an error, not "every screening cancelled".
            raise SourceError(f"{cinema.id} : aucune salle Dulac rattachée à {cinema.source_ref!r}")
        films = body["films_by_id"]
        kept: dict[tuple[str, datetime], tuple[tuple[int, int], RawScreening]] = {}
        n_listed = n_no_film = 0
        for seance in body["seances_week"]:
            salle_id = str(seance.get("salle_id")) if isinstance(seance, dict) else None
            if salle_id not in salles or seance.get("is_cancelled"):
                continue
            n_listed += 1
            film = films.get(str(seance.get("film_id")))
            if not isinstance(film, dict) or not _text(film.get("title")):
                n_no_film += 1
                log.warning("Dulac : séance %s sans fiche film, ignorée", seance.get("id"))
                continue
            screening = parse_seance(seance, film, cinema.id)
            if screening is None or not start <= screening.starts_at < end:
                continue
            show = (salle_id, screening.starts_at)  # same room, same time: same show
            score = _completeness(film, seance)
            previous = kept.get(show)
            if previous is None or score > previous[0]:
                kept[show] = (score, screening)
        if n_listed and n_no_film == n_listed:
            # Film records missing from the payload: the screenings would all be cancelled.
            raise SourceError(f"{cinema.id} : aucune fiche film dans la réponse Dulac")
        return [s for _, s in kept.values()]
