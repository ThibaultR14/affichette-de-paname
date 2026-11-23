"""Source adapters: one module per screening source (see docs/architecture.md).

Each source exposes `fetch(cinema, start, end) -> list[RawScreening]`, with `start <= starts_at
< end`, and raises `SourceError` when the cinema cannot be imported this run (its previous
screenings are then left untouched).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class SourceError(RuntimeError):
    """The source could not be read. The message never contains a full URL or a key."""


@dataclass(frozen=True)
class Cinema:
    id: str
    name: str
    source: str | None
    source_ref: str | None
    website_url: str | None = None


@dataclass(frozen=True)
class RawScreening:
    source_key: str  # stable key of the screening in its source -> idempotent upsert
    cinema_id: str
    raw_title: str
    starts_at: datetime  # timezone-aware
    version: str | None = None  # VO | VOSTFR | VF
    format: str | None = None  # 35mm | 70mm | 16mm | 4K | DCP
    booking_url: str | None = None
    runtime_hint: int | None = None  # minutes, as given by the source
    year_hint: int | None = None
    director_hint: str | None = None
    tmdb_hint: int | None = None
    event_label: str | None = None


class Source(Protocol):
    def fetch(self, cinema: Cinema, start: datetime, end: datetime) -> list[RawScreening]: ...
