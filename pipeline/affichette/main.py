"""Daily import: source -> normalize -> TMDB match -> `films` -> `screenings` -> `import_runs`.

Errors are isolated per cinema: a failed cinema keeps its last known screenings.

From `pipeline/` (reads the repo's `.env`):
    uv run python -m affichette.main --dry-run          # reads the database, writes nothing
    uv run python -m affichette.main --cinema champo    # one cinema (option repeatable)
    uv run python -m affichette.main                    # every cinema with a source
In GitHub Actions, the report also goes to the job summary and a failing cinema opens an
issue (see `report.py`).
Exit code: 0 all ok, 1 at least one cinema failed, 2 bad arguments or configuration.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from affichette.db import Db, DbError, DryRunDb
from affichette.films import ensure_films
from affichette.matching import DbTitleMatchStore, Matcher, MatchQuery
from affichette.normalize import paris_window, to_utc
from affichette.report import (
    GithubIssues,
    open_failure_issues,
    open_global_issue,
    run_url,
    write_step_summary,
)
from affichette.sources import Cinema, Source, SourceError
from affichette.sources.dulac import DulacSource
from affichette.sources.scare import ScareSource
from affichette.tmdb import Tmdb, TmdbError
from affichette.upsert import mark_failed, sync_cinema

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
WINDOW_DAYS = 7  # today included (SPEC)


class UsageError(ValueError):
    """Bad `--cinema` value."""


@dataclass
class CinemaResult:
    cinema_id: str
    status: str  # ok | error
    n_screenings: int = 0
    n_unmatched: int = 0
    n_cancelled: int = 0
    coverage_until: date | None = None
    error: str | None = None


@dataclass
class RunReport:
    results: list[CinemaResult]

    @property
    def failed(self) -> list[CinemaResult]:
        return [r for r in self.results if r.status != "ok"]

    def summary(self) -> str:
        ok = len(self.results) - len(self.failed)
        lines = [f"import : {ok}/{len(self.results)} salle(s) ok"]
        for r in self.results:
            if r.status == "ok":
                until = r.coverage_until.isoformat() if r.coverage_until else "?"
                lines.append(
                    f"  - {r.cinema_id} : {r.n_screenings} séance(s), {r.n_unmatched} sans"
                    f" TMDB, {r.n_cancelled} annulée(s), programme jusqu'au {until}"
                )
            else:
                lines.append(f"  - {r.cinema_id} : ÉCHEC, {r.error}")
        return "\n".join(lines)


def error_message(exc: Exception) -> str:
    """Safe text for logs and `import_runs.error`.

    Our own errors never hold a URL or a key; `requests` errors do, so only their type is kept.
    """
    if isinstance(exc, SourceError | DbError | TmdbError):
        return str(exc)
    if isinstance(exc, requests.RequestException):
        return type(exc).__name__
    return f"{type(exc).__name__}: {exc}"[:500]


def load_cinemas(db: Any) -> list[Cinema]:
    rows = db.select("cinemas", {"select": "id,name,source,source_ref,website_url", "order": "id"})
    return [
        Cinema(r["id"], r["name"], r.get("source"), r.get("source_ref"), r.get("website_url"))
        for r in rows
    ]


def select_cinemas(
    cinemas: list[Cinema], sources: dict[str, Source], only: list[str] | None
) -> list[Cinema]:
    """Cinemas with a source we can import, limited to `only` (unknown id -> UsageError)."""
    importable = {c.id: c for c in cinemas if c.source in sources}
    if not only:
        return list(importable.values())
    by_id = {c.id: c for c in cinemas}
    for cinema_id in only:
        if cinema_id not in by_id:
            raise UsageError(f"salle inconnue : {cinema_id}")
        if cinema_id not in importable:
            raise UsageError(f"{cinema_id} : pas de source importable ({by_id[cinema_id].source})")
    return [importable[c] for c in dict.fromkeys(only)]


def import_cinema(
    cinema: Cinema,
    source: Source,
    db: Any,
    tmdb: Any,
    matcher: Matcher,
    window: tuple[datetime, datetime],
    now: datetime,
) -> CinemaResult:
    raws = source.fetch(cinema, *window)
    matched = []
    for raw in raws:
        query = MatchQuery(
            raw.raw_title,
            cinema.id,
            raw.director_hint,
            raw.year_hint,
            raw.tmdb_hint,
            raw.event_label,
        )
        matched.append((raw, matcher.match(query).tmdb_id))
    valid = ensure_films({t for _, t in matched if t is not None}, tmdb, db, now)
    screenings = [(raw, t if t in valid else None) for raw, t in matched]
    result = sync_cinema(db, cinema.id, screenings, window, now)
    return CinemaResult(
        cinema.id,
        "ok",
        n_screenings=result.n_screenings,
        n_unmatched=sum(1 for _, t in screenings if t is None),
        n_cancelled=result.n_cancelled,
        coverage_until=result.coverage_until,
    )


def _now() -> datetime:
    return datetime.now(UTC)


def run(
    db: Any,
    tmdb: Any,
    sources: dict[str, Source],
    matcher: Matcher,
    now: datetime,
    only: list[str] | None = None,
    clock: Callable[[], datetime] = _now,
) -> RunReport:
    """Import every selected cinema. Raises UsageError before touching anything."""
    now = to_utc(now)
    cinemas = select_cinemas(load_cinemas(db), sources, only)
    window = paris_window(now, WINDOW_DAYS)
    results = []
    for cinema in cinemas:
        started = clock()
        try:
            source = sources[cinema.source or ""]
            result = import_cinema(cinema, source, db, tmdb, matcher, window, now)
        except Exception as exc:  # isolate cinemas: one failure never stops the others
            result = CinemaResult(cinema.id, "error", error=error_message(exc))
            log.error("%s : import en échec, séances conservées : %s", cinema.id, result.error)
            try:
                mark_failed(db, cinema.id, now)
            except DbError as db_exc:
                log.error("%s : échec non enregistré : %s", cinema.id, db_exc)
        results.append(result)
        run_row = {
            "started_at": started.isoformat(),
            "finished_at": clock().isoformat(),
            "cinema_id": cinema.id,
            "status": result.status,
            "n_screenings": result.n_screenings,
            "n_unmatched": result.n_unmatched,
            "error": result.error,
        }
        try:
            db.insert("import_runs", [run_row])
        except DbError as exc:
            log.error("%s : import_runs non écrit : %s", cinema.id, exc)
    try:
        matcher.store.flush()  # title_matches: one upsert for the run
    except DbError as exc:
        log.error("title_matches non écrit : %s", exc)
    return RunReport(results)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import des séances (7 jours).")
    parser.add_argument("--dry-run", action="store_true", help="lit la base, n'écrit rien")
    parser.add_argument(
        "--cinema", action="append", metavar="ID", help="limite à cette salle (répétable)"
    )
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    load_dotenv(REPO_ROOT / ".env")

    try:
        real_db = Db.from_env()
        db: Any = DryRunDb(real_db) if args.dry_run else real_db
        tmdb = Tmdb()
        matcher = Matcher(tmdb, store=DbTitleMatchStore(db))
        sources: dict[str, Source] = {"scare": ScareSource(), "dulac": DulacSource()}
        report = run(db, tmdb, sources, matcher, _now(), args.cinema)
    except UsageError as exc:
        log.error("%s", exc)
        return 2
    except (DbError, TmdbError) as exc:  # nothing imported: configuration or service down
        log.error("%s", exc)
        write_step_summary(f"import : ÉCHEC global, {exc}", os.environ)
        gh = None if args.dry_run else GithubIssues.from_env(os.environ)
        if gh is not None:
            open_global_issue(str(exc), gh, _now(), run_url(os.environ))
        return 2
    text = f"{report.summary()}\n{matcher.report.summary()}"
    print(text)
    write_step_summary(text, os.environ)
    gh = None if args.dry_run else GithubIssues.from_env(os.environ)
    if gh is not None:
        open_failure_issues(report, gh, _now(), run_url(os.environ))
    log.info("TMDB : %(http)d requête(s), %(cache_hits)d depuis le cache", tmdb.stats)
    if isinstance(db, DryRunDb):
        print(db.summary())
    return 1 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
