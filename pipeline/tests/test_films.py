from datetime import UTC, datetime

from affichette.films import film_row, upsert_film
from affichette.tmdb import Cached, slim_movie
from tests.fakes import fixture

FETCHED = datetime(2026, 11, 20, 4, 0, tzinfo=UTC)


class FakeTmdb:
    def __init__(self, data):
        self.data = data
        self.ids = []

    def movie(self, tmdb_id):
        self.ids.append(tmdb_id)
        return Cached(self.data, FETCHED)


class FakeDb:
    def __init__(self):
        self.calls = []

    def upsert(self, table, rows, on_conflict):
        self.calls.append((table, rows, on_conflict))


def test_film_row_from_fixture():
    row = film_row(slim_movie(fixture("tmdb/movie_426.json")), FETCHED)
    assert row == {
        "tmdb_id": 426,
        "title": "Sueurs froides",
        "original_title": "Vertigo",
        "year": 1958,
        "runtime_min": 128,
        "directors": ["Alfred Hitchcock"],
        "overview": "Scottie Ferguson, policier sujet au vertige, est chargé de suivre la femme "
        "d'un ami.",
        "poster_path": "/fixture-poster-426.jpg",
        "tmdb_fetched_at": "2026-11-20T04:00:00+00:00",
    }


def test_film_row_missing_fields():
    row = film_row({"id": 7, "original_title": "Orig", "runtime": 0, "directors": []}, FETCHED)
    assert row["title"] == "Orig"  # title is not null in the schema
    assert row["year"] is None
    assert row["runtime_min"] is None  # no end time shown without a known runtime
    assert row["overview"] is None and row["poster_path"] is None
    assert film_row({"id": 8}, FETCHED)["title"] == "TMDB 8"


def test_upsert_film_writes_row():
    tmdb, db = FakeTmdb(slim_movie(fixture("tmdb/movie_426.json"))), FakeDb()
    row = upsert_film(426, tmdb, db)
    assert tmdb.ids == [426]
    assert db.calls == [("films", [row], "tmdb_id")]
    assert row["title"] == "Sueurs froides"


def test_upsert_film_unknown_movie_writes_nothing():
    db = FakeDb()
    assert upsert_film(999, FakeTmdb(None), db) is None
    assert db.calls == []


def test_upsert_film_dry_run_returns_row_without_db():
    row = upsert_film(426, FakeTmdb(slim_movie(fixture("tmdb/movie_426.json"))), None)
    assert row["tmdb_id"] == 426
