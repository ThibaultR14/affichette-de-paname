"""Write one cinema's screenings: idempotent upsert on `source_key`, then cancellations.

For a cinema whose import succeeded, a future screening of the import window that the source no
longer lists gets `cancelled_at`. A cinema whose import failed is not touched (`mark_failed`
only records the failure on `cinemas`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from affichette.db import DbError, in_list
from affichette.normalize import paris_date, to_utc
from affichette.sources import RawScreening

PAGE_SIZE = 1000  # Supabase `max_rows`
CANCEL_CHUNK = 100  # source keys per PATCH (URL length)


@dataclass(frozen=True)
class SyncResult:
    n_screenings: int
    n_cancelled: int
    coverage_until: date | None


def _ts(dt: datetime) -> str:
    return to_utc(dt).isoformat()


def screening_row(raw: RawScreening, tmdb_id: int | None, now: datetime) -> dict[str, Any]:
    """`screenings` row. `first_seen_at` is left out so an update keeps the first value."""
    return {
        "source_key": raw.source_key,
        "cinema_id": raw.cinema_id,
        "tmdb_id": tmdb_id,
        "raw_title": raw.raw_title,
        "starts_at": _ts(raw.starts_at),
        "version": raw.version,
        "format": raw.format,
        "booking_url": raw.booking_url,
        "last_seen_at": _ts(now),
        "cancelled_at": None,  # listed again: no longer cancelled
    }


def active_keys(db: Any, cinema_id: str, start: datetime, end: datetime) -> set[str]:
    """`source_key` of the cinema's non-cancelled screenings with start <= starts_at < end."""
    keys: set[str] = set()
    offset = 0
    while True:
        rows = db.select(
            "screenings",
            {
                "select": "source_key",
                "cinema_id": f"eq.{cinema_id}",
                "cancelled_at": "is.null",
                "and": f'(starts_at.gte."{_ts(start)}",starts_at.lt."{_ts(end)}")',
                "order": "id",
                "limit": str(PAGE_SIZE),
                "offset": str(offset),
            },
        )
        keys.update(r["source_key"] for r in rows)
        if len(rows) < PAGE_SIZE:
            return keys
        offset += PAGE_SIZE


def sync_cinema(
    db: Any,
    cinema_id: str,
    screenings: list[tuple[RawScreening, int | None]],
    window: tuple[datetime, datetime],
    now: datetime,
) -> SyncResult:
    """Upsert the cinema's screenings of `window`, cancel the vanished future ones, mark ok."""
    start, end = window
    rows: dict[str, dict[str, Any]] = {}
    for raw, tmdb_id in screenings:
        if raw.cinema_id != cinema_id or not start <= raw.starts_at < end:
            raise ValueError(f"séance {raw.source_key} hors de la salle ou de la fenêtre")
        rows[raw.source_key] = screening_row(raw, tmdb_id, now)  # one row per key

    # Only the future part of the window: past screenings stay as history.
    vanished = sorted(active_keys(db, cinema_id, max(now, start), end) - rows.keys())
    db.upsert("screenings", list(rows.values()), on_conflict="source_key")

    coverage = max((paris_date(raw.starts_at) for raw, _ in screenings), default=None)
    state: dict[str, Any] = {
        "last_import_at": _ts(now),
        "last_success_at": _ts(now),
        "last_import_ok": True,
    }
    if coverage is not None:  # nothing scheduled: keep the last known coverage
        state["coverage_until"] = coverage.isoformat()
    try:
        for i in range(0, len(vanished), CANCEL_CHUNK):
            db.update(
                "screenings",
                {"cancelled_at": _ts(now)},
                {"source_key": in_list(vanished[i : i + CANCEL_CHUNK])},
            )
        db.update("cinemas", state, {"id": f"eq.{cinema_id}"})
    except DbError as exc:
        # The screenings are written (each step is idempotent, the next run completes it):
        # the failure must say so instead of claiming the cinema was left untouched.
        raise DbError(f"écriture partielle, séances écrites mais pas finalisées : {exc}") from None
    return SyncResult(len(rows), len(vanished), coverage)


def mark_failed(db: Any, cinema_id: str, now: datetime) -> None:
    """Failed import: only `cinemas` records it. Screenings, coverage and `last_success_at`
    are kept, so the site still dates the programme from the last successful import."""
    db.update(
        "cinemas", {"last_import_at": _ts(now), "last_import_ok": False}, {"id": f"eq.{cinema_id}"}
    )
