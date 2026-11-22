"""TMDB v3 client, ported from Recsys_movie (`pipeline/enrich_tmdb.py`).

- Auth: Bearer read token `TMDB_READ_TOKEN` only (the v3 `api_key` would sit in the URL).
- Rate limited, retries on 429 / 5xx / network errors, honours `Retry-After`.
- Never logs a URL, a query string, a header or the token: only the API path (`/movie/147`).
- Cache: one slim JSON per call in `pipeline/data/cache/tmdb/<kind>/<key>.json` with its fetch
  date. Reused when < 30 days old, deleted when > 6 months old (TMDB terms). Never committed
  (`.gitignore`).
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import random
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

log = logging.getLogger(__name__)

API_BASE = "https://api.themoviedb.org/3"
LANGUAGE = "fr-FR"
CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "cache" / "tmdb"
CACHE_REUSE = timedelta(days=30)
CACHE_MAX_AGE = timedelta(days=182)  # TMDB terms: cached data must not be kept > 6 months

# TMDB docs (rate limiting): upper limit around 40 requests/s, respect 429. We stay at half.
MAX_REQUESTS_PER_SECOND = 20
MAX_RETRIES = 6
MAX_RETRY_DELAY_S = 60
TIMEOUT_S = 20


class TmdbError(RuntimeError):
    """TMDB call failed. The message holds the API path, never the URL or the token."""


class TmdbAuthError(TmdbError):
    """Missing or refused token: retrying will not help."""


@dataclass(frozen=True)
class Cached:
    """A TMDB response (`data`, None for a 404) and when it was fetched from TMDB."""

    data: dict[str, Any] | None
    fetched_at: datetime


# --- Pure helpers ------------------------------------------------------------------------------


def release_year(release_date: str | None) -> int | None:
    if not release_date or len(release_date) < 4 or not release_date[:4].isdigit():
        return None
    return int(release_date[:4])


def slim_movie(raw: dict) -> dict:
    """Keep only what we store from /movie/{id}?append_to_response=credits&language=fr-FR."""
    crew = (raw.get("credits") or {}).get("crew") or []
    directors: list[str] = []
    for person in crew:
        name = person.get("name")
        if person.get("job") == "Director" and name and name not in directors:
            directors.append(name)
    return {
        "id": raw.get("id"),
        "title": raw.get("title") or None,
        "original_title": raw.get("original_title") or None,
        "release_date": raw.get("release_date") or None,
        "runtime": raw.get("runtime") or None,
        "overview": raw.get("overview") or None,
        "poster_path": raw.get("poster_path") or None,
        "directors": directors,
    }


def is_fresh(fetched_at: datetime, now: datetime, max_age: timedelta) -> bool:
    return now - fetched_at < max_age


def _read_entry(file: Path) -> tuple[datetime, Any]:
    entry = json.loads(file.read_text(encoding="utf-8"))
    return datetime.fromisoformat(entry["fetched_at"]), entry["data"]


def purge_old_cache(cache_dir: Path = CACHE_DIR, now: datetime | None = None) -> int:
    """Delete cached responses older than 6 months, unreadable ones and leftover `.tmp` files
    (interrupted writes). Returns the count."""
    now = now or datetime.now(UTC)
    removed = 0
    for file in cache_dir.glob("*/*.tmp"):
        file.unlink()
        removed += 1
    for file in cache_dir.glob("*/*.json"):
        try:
            fetched_at, _ = _read_entry(file)
            old = not is_fresh(fetched_at, now, CACHE_MAX_AGE)
        except (ValueError, KeyError, TypeError):
            old = True  # unreadable entry: refetch
        if old:
            file.unlink()
            removed += 1
    return removed


# --- Client -------------------------------------------------------------------------------------


class RateLimiter:
    def __init__(self, per_second: float, clock: Callable[[], float] = time.monotonic):
        self.interval = 1.0 / per_second
        self.clock = clock
        self.lock = threading.Lock()
        self.next_at = 0.0

    def delay(self) -> float:
        """Reserve the next slot; returns how long the caller must wait before using it."""
        with self.lock:
            now = self.clock()
            at = max(now, self.next_at)
            self.next_at = at + self.interval
        return at - now


def _retry_delay(attempt: int, retry_after: str | None) -> float:
    if retry_after:
        try:
            seconds = float(retry_after)
        except ValueError:
            seconds = math.nan  # HTTP-date form: fall back to backoff
        if math.isfinite(seconds):
            return min(MAX_RETRY_DELAY_S, max(0.0, seconds))
    return min(MAX_RETRY_DELAY_S, 2**attempt) + random.random()


class Tmdb:
    """Minimal TMDB v3 client with a JSON file cache."""

    def __init__(
        self,
        token: str | None = None,
        cache_dir: Path = CACHE_DIR,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        per_second: float = MAX_REQUESTS_PER_SECOND,
    ):
        token = (token if token is not None else os.environ.get("TMDB_READ_TOKEN", "")).strip()
        if not token:
            raise TmdbAuthError("TMDB_READ_TOKEN manquant (variable d'environnement ou .env)")
        self.session = session or requests.Session()
        self.session.headers["Accept"] = "application/json"
        self.session.headers["Authorization"] = f"Bearer {token}"
        self.cache_dir = cache_dir
        # TMDB terms: every run that uses the cache first drops what is older than 6 months.
        removed = purge_old_cache(cache_dir)
        if removed:
            log.info("cache TMDB : %d réponse(s) de plus de 6 mois supprimée(s)", removed)
        self.sleep = sleep
        self.limiter = RateLimiter(per_second)
        self.stats = {"http": 0, "cache_hits": 0, "retries": 0}
        self._stats_lock = threading.Lock()

    def _count(self, key: str) -> None:
        with self._stats_lock:
            self.stats[key] += 1

    def _get(self, path: str, params: dict[str, Any]) -> dict | None:
        """GET with retries. JSON body, or None on 404. Logs `path`, never the URL."""
        for attempt in range(MAX_RETRIES):
            wait = self.limiter.delay()
            if wait > 0:
                self.sleep(wait)
            retry_after = None
            try:
                r = self.session.get(API_BASE + path, params=params, timeout=TIMEOUT_S)
            except requests.RequestException as exc:
                # str(exc) can contain the URL: only the exception type is kept.
                status: int | str = type(exc).__name__
            else:
                self._count("http")
                if r.status_code == 200:
                    try:
                        return r.json()
                    except ValueError:
                        status = "200 non-JSON"  # proxy/CDN error page: retry
                elif r.status_code == 404:
                    return None
                elif r.status_code in (401, 403):
                    raise TmdbAuthError(f"TMDB {r.status_code} sur {path} : jeton refusé")
                elif r.status_code != 429 and r.status_code < 500:
                    raise TmdbError(f"TMDB {r.status_code} sur {path}")
                else:
                    status, retry_after = r.status_code, r.headers.get("Retry-After")
            if attempt == MAX_RETRIES - 1:
                break
            self._count("retries")
            delay = _retry_delay(attempt, retry_after)
            log.warning("TMDB %s sur %s, nouvel essai dans %.0f s", status, path, delay)
            self.sleep(delay)
        raise TmdbError(f"TMDB : abandon sur {path} après {MAX_RETRIES} essais")

    def _cached(self, kind: str, key: str, fetch: Callable[[], dict | None]) -> Cached:
        file = self.cache_dir / kind / f"{key}.json"
        now = datetime.now(UTC)
        if file.exists():
            try:
                fetched_at, data = _read_entry(file)
            except (ValueError, KeyError, TypeError):
                log.warning("cache TMDB illisible, rechargé : %s/%s", kind, key)
            else:
                if is_fresh(fetched_at, now, CACHE_REUSE):
                    self._count("cache_hits")
                    return Cached(data, fetched_at)
        data = fetch()
        fetched_at = datetime.now(UTC).replace(microsecond=0)
        file.parent.mkdir(parents=True, exist_ok=True)
        entry = {"fetched_at": fetched_at.isoformat(), "data": data}
        tmp = file.with_suffix(".tmp")
        tmp.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
        tmp.replace(file)
        return Cached(data, fetched_at)

    def movie(self, tmdb_id: int) -> Cached:
        """Slim /movie/{id} (credits, fr-FR). `data` is None when TMDB has no such movie."""

        def fetch() -> dict | None:
            raw = self._get(
                f"/movie/{tmdb_id}", {"append_to_response": "credits", "language": LANGUAGE}
            )
            return None if raw is None else slim_movie(raw)

        return self._cached("movie", str(int(tmdb_id)), fetch)

    def search_movie(self, query: str, year: int | None = None) -> list[dict]:
        """/search/movie (fr-FR), first page: [{id, title, original_title, release_date}]."""
        params: dict[str, Any] = {"query": query, "language": LANGUAGE, "include_adult": "false"}
        if year:
            params["year"] = int(year)

        def fetch() -> dict:
            raw = self._get("/search/movie", params) or {}
            return {"results": [slim_title(r) for r in raw.get("results") or []]}

        key = cache_key(query, str(year or ""))
        return self._cached("search", key, fetch).data["results"]

    def search_person(self, name: str) -> list[dict]:
        """/search/person, first page: [{id, name, known_for_department}]."""

        def fetch() -> dict:
            raw = self._get("/search/person", {"query": name, "include_adult": "false"}) or {}
            people = [
                {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "known_for_department": p.get("known_for_department"),
                }
                for p in raw.get("results") or []
            ]
            return {"results": people}

        return self._cached("person", cache_key(name), fetch).data["results"]

    def person_directing(self, person_id: int) -> list[dict]:
        """Films the person directed (/person/{id}/movie_credits, crew job Director, fr-FR)."""

        def fetch() -> dict:
            raw = self._get(f"/person/{person_id}/movie_credits", {"language": LANGUAGE}) or {}
            crew = raw.get("crew") or []
            films = [slim_title(c) for c in crew if c.get("job") == "Director"]
            return {"results": films}

        return self._cached("person_credits", str(int(person_id)), fetch).data["results"]


def slim_title(raw: dict) -> dict:
    """What matching needs from a search / credits entry."""
    return {
        "id": raw.get("id"),
        "title": raw.get("title") or None,
        "original_title": raw.get("original_title") or None,
        "release_date": raw.get("release_date") or None,
    }


def cache_key(*parts: str) -> str:
    """Filesystem-safe cache key: readable slug + short hash of the exact query."""
    text = "\x1f".join(parts)
    slug = re.sub(r"[^a-z0-9]+", "_", text.casefold()).strip("_")[:60] or "q"
    return f"{slug}_{hashlib.sha1(text.encode('utf-8')).hexdigest()[:10]}"
