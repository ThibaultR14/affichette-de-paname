"""SCARE open dataset "Programmation des cinémas indépendants" (data.gouv.fr, Licence Ouverte 2.0).

data-fair API, no key. One paginated download of the Paris lines (`cinecp:75*`, ~440 rows) per
run, shared by every SCARE cinema; rows are matched to `cinemas.source_ref` = exact `cinenom`.
See docs/spikes/01-sources.md for the fields.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import requests

from affichette.normalize import normalize_format, normalize_version
from affichette.sources import Cinema, RawScreening, SourceError

log = logging.getLogger(__name__)

API = "https://datacinesindes.fr/data-fair/api/v1/datasets/programmation-cinemas/lines"
PARAMS = {"qs": "cinecp:75*", "size": "1000", "sort": "showstart"}
USER_AGENT = "affichette-de-paname/0.1 (import quotidien, non commercial)"
TIMEOUT_S = 30
MAX_PAGES = 50  # ~440 Paris rows today: 1 page. Guards against a `next` loop.

_VF = {"VF", "VERSION_LOCAL", "VERSION_ORIGINAL_LOCAL"}  # *_LOCAL: French-language film
_VOSTFR = {"VOST", "VOSTFR"}
_VO = {"VO", "VERSION_ORIGINAL"}


def _text(value: Any) -> str | None:
    """SCARE writes missing values as null, "" or the string "null"."""
    if value is None:
        return None
    text = str(value).strip()
    return None if text in ("", "null") else text


def scare_version(version: str | None, audio: str | None) -> str | None:
    """`filmversion` + `filmaudio` -> VO | VOSTFR | VF. "ST" in the audio means subtitled."""
    version = (_text(version) or "").upper()
    subtitled = "ST" in {t.strip().upper() for t in (_text(audio) or "").split(",")}
    if version in _VF:
        return "VF"  # "VF" + "ST,OCAP": French subtitles for the deaf, still VF
    if version in _VOSTFR:
        return "VOSTFR"
    if version in _VO:
        return "VOSTFR" if subtitled else "VO"
    return normalize_version(version)


def parse_row(row: dict[str, Any], cinema_id: str) -> RawScreening | None:
    """One SCARE line -> RawScreening, or None when it has no start time or no show id."""
    start, show_id = _text(row.get("showstart")), _text(row.get("showid"))
    title = _text(row.get("filmtitle"))
    if not start or not show_id or not title:
        return None
    try:
        starts_at = datetime.fromisoformat(start)
    except ValueError:
        log.warning("SCARE : horaire illisible %r (séance %s), ignorée", start, show_id)
        return None
    if starts_at.tzinfo is None:
        log.warning("SCARE : horaire sans fuseau %r (séance %s), ignorée", start, show_id)
        return None
    duration = row.get("filmduration")  # seconds (5160 for an 86-minute film)
    runtime = round(duration / 60) if isinstance(duration, int | float) and duration > 0 else None
    tmdb_hint = row.get("_donnees_imdb.id")
    return RawScreening(
        source_key=f"scare:{cinema_id}:{show_id}",
        cinema_id=cinema_id,
        raw_title=title,
        starts_at=starts_at,
        version=scare_version(row.get("filmversion"), row.get("filmaudio")),
        format=normalize_format(title) or normalize_format(_text(row.get("description"))),
        booking_url=_text(row.get("showurl")),
        runtime_hint=runtime,
        director_hint=_text(row.get("filmdirector")),
        tmdb_hint=int(tmdb_hint) if isinstance(tmdb_hint, int | float) and tmdb_hint else None,
        event_label=_text(row.get("evenement")),
    )


class ScareSource:
    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self._rows: list[dict[str, Any]] | None = None
        self._error: SourceError | None = None

    def rows(self) -> list[dict[str, Any]]:
        """All Paris lines, downloaded once per run (a failure is remembered too)."""
        if self._error is not None:
            raise self._error
        if self._rows is None:
            try:
                self._rows = self._download()
            except SourceError as exc:
                self._error = exc
                raise
        return self._rows

    def _download(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        url: str | None = API
        params: dict[str, str] | None = PARAMS
        for _ in range(MAX_PAGES):
            try:
                r = self.session.get(url, params=params, timeout=TIMEOUT_S)
            except requests.RequestException as exc:
                # str(exc) contains the URL: keep the type only.
                raise SourceError(f"SCARE injoignable ({type(exc).__name__})") from None
            if r.status_code != 200:
                raise SourceError(f"SCARE : HTTP {r.status_code}")
            try:
                body = r.json()
                rows.extend(body["results"])
            except (ValueError, KeyError, TypeError):
                raise SourceError("SCARE : réponse illisible") from None
            url, params = body.get("next"), None  # `next` already carries the query
            if not url:
                break
        else:
            raise SourceError(f"SCARE : plus de {MAX_PAGES} pages, arrêt")
        if not rows:
            # An empty Paris dataset is an outage, not "every screening was cancelled".
            raise SourceError("SCARE : aucune séance parisienne dans le jeu de données")
        return rows

    def fetch(self, cinema: Cinema, start: datetime, end: datetime) -> list[RawScreening]:
        if not cinema.source_ref:
            raise SourceError(f"{cinema.id} : source_ref SCARE manquant")
        rows = [r for r in self.rows() if r.get("cinenom") == cinema.source_ref]
        if not rows:
            # Renamed or removed from the dataset: an error, not "every screening cancelled".
            # A cinema listed with no screening this week is still a successful import.
            raise SourceError(f"{cinema.id} : salle absente du jeu SCARE ({cinema.source_ref!r})")
        out = []
        for row in rows:
            screening = parse_row(row, cinema.id)
            if screening is not None and start <= screening.starts_at < end:
                out.append(screening)
        return out
