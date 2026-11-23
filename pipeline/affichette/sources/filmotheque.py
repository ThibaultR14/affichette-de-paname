"""Filmothèque du Quartier Latin: HTML of lafilmotheque.fr (WordPress, rendered server-side).

The home page lists the films of the current and the next week (`#front-this_week` cards and the
two timetable overlays); each film page `/films/<slug>/` gives its screenings in plain text:
"Cette semaine" / "Prochainement" blocks, one timetable per room (class R = Salle Marilyn,
B = Salle Audrey), days as "Mercredi 18" (no month) and times as "17H50" (Europe/Paris).
The overlay grids are only used to list films: a day there is only given by a CSS position.

Quirks:
- the published time is when the session opens; the film starts 10 min later (not applied);
- the same screening can be listed twice ("Mercredi 18" and "mercredi 18"): merged on its key;
- no version and no booking link per screening (the front falls back to the cinema website).
See docs/spikes/01-sources.md.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta
from urllib.parse import unquote, urlsplit

import requests
from bs4 import BeautifulSoup, Tag

from affichette.normalize import PARIS, normalize_format, normalize_version, paris_date, to_utc
from affichette.sources import Cinema, RawScreening, SourceError

HOME = "https://lafilmotheque.fr/"
FILM_PATH = "/films/"
USER_AGENT = "affichette-de-paname/0.1 (import quotidien, non commercial)"
TIMEOUT_S = 30
DELAY_S = 1.0  # between two film pages
MAX_FILMS = 120  # more links than that: the page is not the one we know
# Where films are listed on the home page (the header "next sessions" is a subset).
FILM_LIST_SELECTORS = ("#front-this_week", "#overlay-programmation", "#overlay-programmation-next")

WEEKDAYS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
_DAY_LABEL = re.compile(r"^\s*(\w+)\s+(\d{1,2})\b")
_HOURS = re.compile(r"^\s*(\d{1,2})\s*[hH]\s*(\d{2})\s*$")
_YEAR = re.compile(r"^\s*(\d{4})\s*$")
# A screening listed at 00:30 under "mardi 24" is on the night of the 24th to the 25th.
AFTER_MIDNIGHT_BEFORE = 5
_ROOMS = {"R", "B"}


def _text(node: Tag | None) -> str | None:
    if node is None:
        return None
    text = " ".join(node.get_text(" ", strip=True).split())
    return text or None


def film_links(home_html: str) -> list[str]:
    """Film page URLs listed on the home page for the current and next week, deduplicated."""
    soup = BeautifulSoup(home_html, "html.parser")
    links: dict[str, None] = {}
    for selector in FILM_LIST_SELECTORS:
        for block in soup.select(selector):
            for a in block.select("a[href]"):
                href = str(a["href"]).split("#")[0]
                parts = urlsplit(href)
                if parts.netloc not in ("", "lafilmotheque.fr", "www.lafilmotheque.fr"):
                    continue
                if parts.path.startswith(FILM_PATH) and parts.path.strip("/") != "films":
                    links[f"https://lafilmotheque.fr{parts.path}"] = None
    return list(links)


def film_slug(url: str) -> str:
    """'https://lafilmotheque.fr/films/ohong-village-%e8%9a%b5/' -> 'ohong-village-蚵'."""
    return unquote(urlsplit(url).path[len(FILM_PATH) :].strip("/"))


def resolve_day(label: str, today: date) -> date | None:
    """'Mercredi 18' -> the only date of [today - 7 d, today + 21 d] with that weekday and day."""
    m = _DAY_LABEL.match(label.lower())
    if not m or m.group(1) not in WEEKDAYS:
        return None
    weekday, day = WEEKDAYS.index(m.group(1)), int(m.group(2))
    matches = [
        d
        for d in (today + timedelta(days=i) for i in range(-7, 22))
        if d.day == day and d.weekday() == weekday
    ]
    return matches[0] if len(matches) == 1 else None


def parse_hours(raw: str) -> tuple[int, int] | None:
    """'17H50' -> (17, 50); also used for durations ('01H55')."""
    m = _HOURS.match(raw)
    if not m:
        return None
    hours, minutes = int(m.group(1)), int(m.group(2))
    return (hours, minutes) if hours < 24 and minutes < 60 else None


def parse_duration(raw: str) -> int | None:
    hm = parse_hours(raw)
    return hm[0] * 60 + hm[1] if hm and hm != (0, 0) else None


def _room(node: Tag) -> str | None:
    classes = set(node.get("class") or [])
    rooms = classes & _ROOMS
    return rooms.pop() if len(rooms) == 1 else None


def parse_film_page(html: str, slug: str, cinema_id: str, today: date) -> list[RawScreening]:
    """Every screening of a film page (both weeks), deduplicated, in no particular order.

    An unreadable room, day or time raises `SourceError`: skipping it would mark the screenings
    already imported for that block as cancelled.
    """
    soup = BeautifulSoup(html, "html.parser")
    infos = soup.select_one(".movie-infos")
    title = _text(infos.select_one("h1") if infos else soup.select_one("main h1"))
    if not title:
        raise SourceError(f"{cinema_id} : fiche film sans titre ({slug})")
    generic = [_text(li) or "" for li in (infos.select("ul.generic li") if infos else [])]
    year = next((int(m.group(1)) for g in generic if (m := _YEAR.match(g))), None)
    runtime = next((d for g in generic if (d := parse_duration(g))), None)
    fmt = next((f for g in generic if (f := normalize_format(g))), None)
    if fmt is None:  # "projection en 35mm" in the presentation text
        fmt = normalize_format(_text(soup.select_one(".presentation")))
    version = next((v for g in generic if (v := normalize_version(g))), None)
    director = _text(infos.select_one(".director")) if infos else None

    screenings: dict[str, RawScreening] = {}
    for timetable in soup.select(".movie-programmation .movie-timetable"):
        room = _room(timetable)
        if room is None:
            raise SourceError(f"{cinema_id} : salle inconnue {timetable.get('class')} ({slug})")
        for day_node in timetable.select(".day"):
            label = _text(day_node.select_one(".day-title")) or ""
            day = resolve_day(label, today)
            if day is None:
                raise SourceError(f"{cinema_id} : jour illisible {label!r} ({slug})")
            for hour_node in day_node.select(".day-hours > div"):
                hm = parse_hours(_text(hour_node) or "")
                if hm is None:
                    raw = _text(hour_node)
                    raise SourceError(f"{cinema_id} : horaire illisible {raw!r} ({slug})")
                shift = 1 if hm[0] < AFTER_MIDNIGHT_BEFORE else 0
                local = datetime(day.year, day.month, day.day, *hm, tzinfo=PARIS)
                local += timedelta(days=shift)
                key = f"filmotheque:{slug}:{room}:{local.strftime('%Y-%m-%dT%H:%M')}"
                screenings[key] = RawScreening(
                    source_key=key,
                    cinema_id=cinema_id,
                    raw_title=title,
                    starts_at=to_utc(local),
                    version=version,
                    format=fmt,
                    booking_url=None,
                    runtime_hint=runtime,
                    year_hint=year,
                    director_hint=director,
                )
    return list(screenings.values())


class FilmothequeSource:
    def __init__(
        self,
        session: requests.Session | None = None,
        delay_s: float = DELAY_S,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.delay_s = delay_s
        self.sleep = sleep

    def _get(self, url: str, what: str) -> str:
        try:
            r = self.session.get(url, timeout=TIMEOUT_S)
        except requests.RequestException as exc:
            # str(exc) contains the URL: keep the type only.
            raise SourceError(f"Filmothèque injoignable ({what}, {type(exc).__name__})") from None
        if r.status_code != 200:
            raise SourceError(f"Filmothèque : HTTP {r.status_code} ({what})")
        return r.content.decode("utf-8", errors="replace")

    def fetch(self, cinema: Cinema, start: datetime, end: datetime) -> list[RawScreening]:
        links = film_links(self._get(HOME, "accueil"))
        if not links:
            raise SourceError(f"{cinema.id} : aucun film sur l'accueil de la Filmothèque")
        if len(links) > MAX_FILMS:
            raise SourceError(f"{cinema.id} : {len(links)} films sur l'accueil, page inattendue")
        today = paris_date(start)
        screenings: list[RawScreening] = []
        for i, url in enumerate(links):
            if i and self.delay_s:
                self.sleep(self.delay_s)
            slug = film_slug(url)
            # One missing film page would mark its screenings cancelled: fail the cinema.
            html = self._get(url, f"fiche {slug}")
            screenings += parse_film_page(html, slug, cinema.id, today)
        if not screenings:
            raise SourceError(f"{cinema.id} : aucune séance lue sur {len(links)} fiches film")
        return [s for s in screenings if start <= s.starts_at < end]
