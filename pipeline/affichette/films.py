"""TMDB movie -> row of the `films` table.

Manual check (from `pipeline/`, reads the repo's `.env`):
    uv run python -m affichette.films 426 147 --dry-run   # prints the rows, writes nothing
    uv run python -m affichette.films 426                 # upserts into Supabase
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from affichette.db import Db, DbError
from affichette.tmdb import CACHE_REUSE, Tmdb, TmdbError, release_year

log = logging.getLogger(__name__)

FILMS_CHUNK = 200  # ids per `in.(...)` select (URL length)

REPO_ROOT = Path(__file__).resolve().parents[2]


def film_row(movie: dict, fetched_at: datetime) -> dict[str, Any]:
    """Slim TMDB movie (see `tmdb.slim_movie`) -> `films` row. `title` is never null."""
    runtime = movie.get("runtime")
    return {
        "tmdb_id": movie["id"],
        "title": movie.get("title") or movie.get("original_title") or f"TMDB {movie['id']}",
        "original_title": movie.get("original_title"),
        "year": release_year(movie.get("release_date")),
        "runtime_min": runtime if isinstance(runtime, int) and runtime > 0 else None,
        "directors": list(movie.get("directors") or []),
        "overview": movie.get("overview") or None,
        "poster_path": movie.get("poster_path"),
        # When TMDB served the data (cache date), for the 30-day refresh and 6-month purge.
        "tmdb_fetched_at": fetched_at.isoformat(),
    }


def upsert_film(tmdb_id: int, tmdb: Tmdb, db: Db | None) -> dict[str, Any] | None:
    """Fetch the movie (fr-FR, cached) and upsert it into `films`. None if unknown to TMDB.

    With `db=None`, nothing is written (dry run) and the row is still returned.
    """
    cached = tmdb.movie(tmdb_id)
    if cached.data is None:
        log.warning("TMDB : film %s introuvable, rien écrit", tmdb_id)
        return None
    row = film_row(cached.data, cached.fetched_at)
    if db is not None:
        db.upsert("films", [row], on_conflict="tmdb_id")
    return row


def ensure_films(tmdb_ids: set[int], tmdb: Tmdb, db: Any, now: datetime) -> set[int]:
    """Make sure every id has a fresh `films` row; return the ids that exist in `films`.

    Absent or older than 30 days -> fetched (TMDB cache) and upserted. An id TMDB does not know
    (404) and that is not in `films` is left out: a screening cannot point to it (foreign key).
    """
    if not tmdb_ids:
        return set()
    known: dict[int, datetime] = {}
    ids = sorted(tmdb_ids)
    for i in range(0, len(ids), FILMS_CHUNK):
        chunk = ",".join(str(x) for x in ids[i : i + FILMS_CHUNK])
        for row in db.select(
            "films", {"select": "tmdb_id,tmdb_fetched_at", "tmdb_id": f"in.({chunk})"}
        ):
            known[row["tmdb_id"]] = datetime.fromisoformat(row["tmdb_fetched_at"])
    valid = set()
    for tmdb_id in ids:
        fetched_at = known.get(tmdb_id)
        if fetched_at is not None and now - fetched_at < CACHE_REUSE:
            valid.add(tmdb_id)
        elif upsert_film(tmdb_id, tmdb, db) is not None or fetched_at is not None:
            valid.add(tmdb_id)
    return valid


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Remplit la table films depuis TMDB.")
    parser.add_argument("tmdb_ids", nargs="+", type=int)
    parser.add_argument("--dry-run", action="store_true", help="affiche les lignes sans écrire")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    load_dotenv(REPO_ROOT / ".env")

    try:
        tmdb = Tmdb()
        db = None if args.dry_run else Db.from_env()
        for tmdb_id in args.tmdb_ids:
            row = upsert_film(tmdb_id, tmdb, db)
            if row is not None:
                print(json.dumps(row, ensure_ascii=False))
    except (TmdbError, DbError) as exc:
        log.error("%s", exc)
        return 1
    log.info("TMDB : %(http)d requête(s), %(cache_hits)d depuis le cache", tmdb.stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
