from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from affichette.db import DbError
from affichette.normalize import paris_window
from affichette.sources import RawScreening
from affichette.upsert import mark_failed, sync_cinema
from tests.fakes import FakeDb

NOW = datetime(2026, 11, 22, 4, 0, tzinfo=UTC)  # 05:00 in Paris
WINDOW = paris_window(NOW, 7)


def show(n: int, starts_at: datetime, **kw) -> RawScreening:
    return RawScreening(f"scare:champo:{n}", "champo", f"FILM {n}", starts_at, **kw)


TONIGHT = datetime(2026, 11, 22, 19, 0, tzinfo=UTC)
TOMORROW = datetime(2026, 11, 23, 19, 0, tzinfo=UTC)
LAST_DAY = datetime(2026, 11, 28, 20, 0, tzinfo=UTC)


def db() -> FakeDb:
    return FakeDb(now=NOW, cinemas=[{"id": "champo"}, {"id": "louxor"}])


def screenings(fake: FakeDb) -> dict[str, dict]:
    return {r["source_key"]: r for r in fake.tables.get("screenings", [])}


def test_first_import_writes_rows_and_cinema_state():
    fake = db()
    rows = [(show(1, TONIGHT, version="VO", format="35mm"), 274), (show(2, LAST_DAY), None)]
    result = sync_cinema(fake, "champo", rows, WINDOW, NOW)
    assert result.n_screenings == 2
    assert result.n_cancelled == 0
    assert result.coverage_until.isoformat() == "2026-11-28"
    one = screenings(fake)["scare:champo:1"]
    assert one["tmdb_id"] == 274
    assert one["starts_at"] == "2026-11-22T19:00:00+00:00"  # UTC
    assert (one["version"], one["format"], one["cancelled_at"]) == ("VO", "35mm", None)
    (champo,) = [c for c in fake.tables["cinemas"] if c["id"] == "champo"]
    assert champo["last_import_ok"] is True
    assert champo["coverage_until"] == "2026-11-28"
    assert champo["last_import_at"] == NOW.isoformat()
    assert champo["last_success_at"] == NOW.isoformat()


def test_rerun_creates_no_duplicate_and_keeps_first_seen():
    fake = db()
    rows = [(show(1, TONIGHT), 274), (show(2, TOMORROW), None)]
    sync_cinema(fake, "champo", rows, WINDOW, NOW)
    first_seen = screenings(fake)["scare:champo:1"]["first_seen_at"]
    later = NOW + timedelta(hours=1)
    fake.now = later
    result = sync_cinema(fake, "champo", rows, WINDOW, later)
    assert len(fake.tables["screenings"]) == 2
    assert result.n_cancelled == 0
    one = screenings(fake)["scare:champo:1"]
    assert one["first_seen_at"] == first_seen
    assert one["last_seen_at"] == later.isoformat()


def test_same_key_twice_in_one_import_is_one_row():
    fake = db()
    result = sync_cinema(
        fake, "champo", [(show(1, TONIGHT), 1), (show(1, TONIGHT), 1)], WINDOW, NOW
    )
    assert result.n_screenings == 1
    assert len(fake.tables["screenings"]) == 1


def test_vanished_future_screening_is_cancelled_then_restored():
    fake = db()
    sync_cinema(fake, "champo", [(show(1, TONIGHT), 1), (show(2, TOMORROW), 2)], WINDOW, NOW)
    result = sync_cinema(fake, "champo", [(show(1, TONIGHT), 1)], WINDOW, NOW)
    assert result.n_cancelled == 1
    assert screenings(fake)["scare:champo:2"]["cancelled_at"] == NOW.isoformat()
    assert screenings(fake)["scare:champo:1"]["cancelled_at"] is None
    # Listed again by a later import: no longer cancelled.
    result = sync_cinema(
        fake, "champo", [(show(1, TONIGHT), 1), (show(2, TOMORROW), 2)], WINDOW, NOW
    )
    assert result.n_cancelled == 0
    assert screenings(fake)["scare:champo:2"]["cancelled_at"] is None


def test_past_and_out_of_window_screenings_are_kept():
    fake = db()
    past = {  # started this morning, before the import: history, not a cancellation
        "source_key": "scare:champo:past",
        "cinema_id": "champo",
        "starts_at": "2026-11-22T00:30:00+00:00",
        "cancelled_at": None,
    }
    beyond = {**past, "source_key": "scare:champo:beyond", "starts_at": "2026-12-10T19:00:00+00:00"}
    other = {**past, "source_key": "scare:louxor:9", "cinema_id": "louxor"}
    other["starts_at"] = TOMORROW.isoformat()  # another cinema
    fake.tables["screenings"] = [past, beyond, other]
    result = sync_cinema(fake, "champo", [(show(1, TONIGHT), 1)], WINDOW, NOW)
    assert result.n_cancelled == 0
    kept = ("scare:champo:past", "scare:champo:beyond", "scare:louxor:9")
    assert all(screenings(fake)[k]["cancelled_at"] is None for k in kept)


def test_successful_empty_import_cancels_and_keeps_coverage():
    fake = db()
    sync_cinema(fake, "champo", [(show(1, TOMORROW), 1)], WINDOW, NOW)
    result = sync_cinema(fake, "champo", [], WINDOW, NOW)
    assert result.n_cancelled == 1
    assert result.coverage_until is None
    (champo,) = [c for c in fake.tables["cinemas"] if c["id"] == "champo"]
    assert champo["coverage_until"] == "2026-11-23"  # last known coverage kept
    assert champo["last_import_ok"] is True


def test_screening_outside_window_is_refused():
    fake = db()
    late = show(1, datetime(2026, 12, 10, 19, 0, tzinfo=UTC))
    try:
        sync_cinema(fake, "champo", [(late, 1)], WINDOW, NOW)
    except ValueError as exc:
        assert "hors" in str(exc)
    else:
        raise AssertionError("expected ValueError")
    assert "screenings" not in fake.tables


def test_mark_failed_touches_only_the_cinema_state():
    fake = db()
    sync_cinema(fake, "champo", [(show(1, TOMORROW), 1)], WINDOW, NOW)
    before = [dict(r) for r in fake.tables["screenings"]]
    later = NOW + timedelta(days=1)
    mark_failed(fake, "champo", later)
    assert fake.tables["screenings"] == before
    (champo,) = [c for c in fake.tables["cinemas"] if c["id"] == "champo"]
    assert champo["last_import_ok"] is False
    assert champo["last_import_at"] == later.isoformat()  # last attempt
    assert champo["last_success_at"] == NOW.isoformat()  # last success kept
    assert champo["coverage_until"] == "2026-11-23"


def test_cancellations_are_chunked(monkeypatch):
    monkeypatch.setattr("affichette.upsert.CANCEL_CHUNK", 2)
    fake = db()
    rows = [(replace(show(i, TOMORROW), source_key=f'scare:champo:"{i},x'), None) for i in range(5)]
    sync_cinema(fake, "champo", rows, WINDOW, NOW)
    result = sync_cinema(fake, "champo", [], WINDOW, NOW)
    assert result.n_cancelled == 5  # keys with quotes and commas survive the `in.(...)` filter
    assert all(r["cancelled_at"] == NOW.isoformat() for r in fake.tables["screenings"])
    assert fake.writes.count(("update", "screenings")) == 3


def test_failure_after_the_upsert_says_the_write_is_partial():
    fake = db()
    sync_cinema(fake, "champo", [(show(1, TONIGHT), 1), (show(2, TOMORROW), 2)], WINDOW, NOW)
    fake.fail_on.add(("update", "screenings"))
    with pytest.raises(DbError, match="écriture partielle"):
        sync_cinema(fake, "champo", [(show(1, TONIGHT), 1)], WINDOW, NOW)
    # The next run completes the cancellation (every step is idempotent).
    fake.fail_on.clear()
    assert sync_cinema(fake, "champo", [(show(1, TONIGHT), 1)], WINDOW, NOW).n_cancelled == 1
