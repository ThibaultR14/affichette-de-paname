import json
import logging
from datetime import UTC, datetime, timedelta

import pytest

from affichette import tmdb as tmdb_mod
from affichette.tmdb import (
    MAX_RETRIES,
    RateLimiter,
    Tmdb,
    TmdbAuthError,
    TmdbError,
    purge_old_cache,
    release_year,
    slim_movie,
)
from tests.fakes import FakeResponse, FakeSession, connection_error, fixture

TOKEN = "secret-read-token-123"


def make_client(tmp_path, *responses, sleeps=None):
    session = FakeSession(*responses)
    sleeps = sleeps if sleeps is not None else []
    client = Tmdb(token=TOKEN, cache_dir=tmp_path, session=session, sleep=sleeps.append)
    client.limiter.delay = lambda: 0.0  # rate limiting has its own test
    return client, session


def write_cache(tmp_path, kind, key, fetched_at, data):
    file = tmp_path / kind / f"{key}.json"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps({"fetched_at": fetched_at.isoformat(), "data": data}), "utf-8")
    return file


# --- helpers ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("date", "year"), [("1958-05-09", 1958), ("1958", 1958), ("", None), (None, None), ("x", None)]
)
def test_release_year(date, year):
    assert release_year(date) == year


def test_slim_movie_keeps_stored_fields_and_dedupes_directors():
    slim = slim_movie(fixture("tmdb/movie_426.json"))
    assert slim == {
        "id": 426,
        "title": "Sueurs froides",
        "original_title": "Vertigo",
        "release_date": "1958-05-09",
        "runtime": 128,
        "overview": "Scottie Ferguson, policier sujet au vertige, est chargé de suivre la femme "
        "d'un ami.",
        "poster_path": "/fixture-poster-426.jpg",
        "directors": ["Alfred Hitchcock"],
    }


def test_slim_movie_empty_fields_become_none():
    slim = slim_movie({"id": 1, "title": "", "runtime": 0, "overview": "", "credits": None})
    assert slim["title"] is None and slim["runtime"] is None and slim["overview"] is None
    assert slim["directors"] == []


def test_rate_limiter_spaces_requests():
    clock = iter([0.0, 0.0, 0.0, 1.0])
    limiter = RateLimiter(per_second=4, clock=lambda: next(clock))
    assert [limiter.delay() for _ in range(4)] == [0.0, 0.25, 0.5, 0.0]


def test_client_waits_for_rate_limiter(tmp_path):
    sleeps = []
    session = FakeSession(FakeResponse(404), FakeResponse(404))
    client = Tmdb(token=TOKEN, cache_dir=tmp_path, session=session, sleep=sleeps.append)
    client.limiter = RateLimiter(per_second=2, clock=lambda: 0.0)
    client.movie(1)
    client.movie(2)
    assert sleeps == [0.5]


# --- auth and request ---------------------------------------------------------------------------


def test_missing_token_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("TMDB_READ_TOKEN", raising=False)
    with pytest.raises(TmdbAuthError, match="TMDB_READ_TOKEN"):
        Tmdb(cache_dir=tmp_path, session=FakeSession())


def test_token_read_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("TMDB_READ_TOKEN", f"  {TOKEN}\n")
    session = FakeSession()
    Tmdb(cache_dir=tmp_path, session=session)
    assert session.headers["Authorization"] == f"Bearer {TOKEN}"


def test_movie_sends_bearer_and_fr_fr_without_key_in_params(tmp_path):
    client, session = make_client(tmp_path, FakeResponse(200, fixture("tmdb/movie_426.json")))
    cached = client.movie(426)
    assert cached.data["title"] == "Sueurs froides"
    assert session.headers["Authorization"] == f"Bearer {TOKEN}"
    (call,) = session.calls
    assert call["url"] == "https://api.themoviedb.org/3/movie/426"
    assert call["params"] == {"append_to_response": "credits", "language": "fr-FR"}
    assert TOKEN not in json.dumps(call["params"])


def test_404_returns_none_and_is_cached(tmp_path):
    client, session = make_client(tmp_path, FakeResponse(404))
    assert client.movie(999).data is None
    assert client.movie(999).data is None  # second call served by the cache
    assert len(session.calls) == 1


@pytest.mark.parametrize("status", [401, 403])
def test_refused_token_raises_auth_error(tmp_path, status):
    client, _ = make_client(tmp_path, FakeResponse(status))
    with pytest.raises(TmdbAuthError, match=f"{status} sur /movie/1"):
        client.movie(1)


def test_other_4xx_not_retried(tmp_path):
    client, session = make_client(tmp_path, FakeResponse(400))
    with pytest.raises(TmdbError, match="400"):
        client.movie(1)
    assert len(session.calls) == 1


# --- retries ------------------------------------------------------------------------------------


def test_429_retries_after_retry_after(tmp_path):
    sleeps = []
    client, session = make_client(
        tmp_path,
        FakeResponse(429, headers={"Retry-After": "3"}),
        FakeResponse(200, fixture("tmdb/movie_426.json")),
        sleeps=sleeps,
    )
    assert client.movie(426).data["id"] == 426
    assert len(session.calls) == 2
    assert sleeps == [3.0]
    assert client.stats["retries"] == 1


def test_5xx_and_network_errors_are_retried(tmp_path):
    client, session = make_client(
        tmp_path,
        FakeResponse(503),
        connection_error(),
        FakeResponse(200, fixture("tmdb/movie_426.json")),
    )
    assert client.movie(426).data["id"] == 426
    assert len(session.calls) == 3


def test_200_with_non_json_body_is_retried(tmp_path):
    client, session = make_client(
        tmp_path,
        FakeResponse(200, "<html>Bad gateway</html>"),
        FakeResponse(200, fixture("tmdb/movie_426.json")),
    )
    assert client.movie(426).data["id"] == 426
    assert len(session.calls) == 2


@pytest.mark.parametrize(
    ("retry_after", "expected"), [("86400", 60.0), ("inf", None), ("-5", 0.0), ("Wed, 21", None)]
)
def test_retry_after_is_capped(tmp_path, retry_after, expected):
    sleeps = []
    client, _ = make_client(
        tmp_path,
        FakeResponse(429, headers={"Retry-After": retry_after}),
        FakeResponse(404),
        sleeps=sleeps,
    )
    client.movie(1)
    (delay,) = sleeps
    if expected is None:  # unusable header: exponential backoff, attempt 0
        assert 1 <= delay < 2
    else:
        assert delay == expected


def test_gives_up_after_max_retries(tmp_path):
    client, session = make_client(tmp_path, *[FakeResponse(429)] * MAX_RETRIES)
    with pytest.raises(TmdbError, match="abandon sur /movie/1"):
        client.movie(1)
    assert len(session.calls) == MAX_RETRIES


def test_logs_and_errors_never_contain_url_or_token(tmp_path, caplog):
    caplog.set_level(logging.DEBUG)
    client, _ = make_client(
        tmp_path,
        FakeResponse(429, headers={"Retry-After": "1"}),
        *[connection_error()] * (MAX_RETRIES - 1),
    )
    with pytest.raises(TmdbError) as err:
        client.movie(426)
    assert caplog.records, "retries should be logged"
    # No chained requests exception (its message holds the URL) in the traceback.
    assert err.value.__cause__ is None and err.value.__context__ is None
    texts = [r.getMessage() for r in caplog.records] + [str(err.value)]
    for text in texts:
        assert TOKEN not in text
        assert "themoviedb.org" not in text
        assert "language=" not in text
    assert "/movie/426" in caplog.text


# --- cache --------------------------------------------------------------------------------------


def test_fresh_cache_is_reused_without_http(tmp_path):
    fetched = datetime.now(UTC) - timedelta(days=29)
    write_cache(tmp_path, "movie", "426", fetched, {"id": 426, "title": "En cache"})
    client, session = make_client(tmp_path)
    cached = client.movie(426)
    assert cached.data["title"] == "En cache"
    assert cached.fetched_at == fetched
    assert session.calls == []
    assert client.stats["cache_hits"] == 1


def test_cache_older_than_30_days_is_refetched(tmp_path):
    write_cache(tmp_path, "movie", "426", datetime.now(UTC) - timedelta(days=31), {"id": 0})
    client, session = make_client(tmp_path, FakeResponse(200, fixture("tmdb/movie_426.json")))
    before = datetime.now(UTC).replace(microsecond=0)
    cached = client.movie(426)
    assert cached.data["title"] == "Sueurs froides"
    assert cached.fetched_at >= before
    assert len(session.calls) == 1
    stored = json.loads((tmp_path / "movie" / "426.json").read_text("utf-8"))
    assert stored["data"]["title"] == "Sueurs froides"
    assert "credits" not in stored["data"]  # slim entry only


def test_unreadable_cache_entry_is_refetched(tmp_path):
    (tmp_path / "movie").mkdir()
    (tmp_path / "movie" / "426.json").write_text("{pas du json", "utf-8")
    client, session = make_client(tmp_path, FakeResponse(200, fixture("tmdb/movie_426.json")))
    assert client.movie(426).data["id"] == 426
    assert len(session.calls) == 1


def test_purge_removes_entries_older_than_6_months(tmp_path):
    now = datetime(2026, 11, 22, tzinfo=UTC)
    recent = write_cache(tmp_path, "movie", "1", now - timedelta(days=100), {"id": 1})
    old = write_cache(tmp_path, "movie", "2", now - timedelta(days=183), {"id": 2})
    broken = tmp_path / "movie" / "3.json"
    broken.write_text("{}", "utf-8")
    leftover = tmp_path / "movie" / "4.tmp"  # interrupted write
    leftover.write_text("{}", "utf-8")
    assert purge_old_cache(tmp_path, now=now) == 3
    assert recent.exists() and not old.exists() and not broken.exists()
    assert not leftover.exists()


def test_client_purges_old_cache_on_start(tmp_path):
    old = write_cache(tmp_path, "movie", "2", datetime.now(UTC) - timedelta(days=200), {"id": 2})
    make_client(tmp_path)
    assert not old.exists()


def test_default_cache_dir_is_git_ignored():
    # pipeline/data/cache/* is in .gitignore: the TMDB cache must never be committed.
    assert tmdb_mod.CACHE_DIR.parts[-3:] == ("data", "cache", "tmdb")
    gitignore = (tmdb_mod.CACHE_DIR.parents[3] / ".gitignore").read_text("utf-8")
    assert "pipeline/data/cache/*" in gitignore.splitlines()


# --- search -------------------------------------------------------------------------------------


def test_search_movie_params_slim_results_and_cache(tmp_path):
    body = {
        "results": [
            {
                "id": 426,
                "title": "Sueurs froides",
                "original_title": "Vertigo",
                "release_date": "1958-05-09",
                "overview": "dropped",
                "popularity": 12.3,
            }
        ]
    }
    client, session = make_client(tmp_path, FakeResponse(200, body))
    expected = [
        {
            "id": 426,
            "title": "Sueurs froides",
            "original_title": "Vertigo",
            "release_date": "1958-05-09",
        }
    ]
    assert client.search_movie("Vertigo", year=1958) == expected
    (call,) = session.calls
    assert call["url"].endswith("/search/movie")
    assert call["params"] == {
        "query": "Vertigo",
        "language": "fr-FR",
        "include_adult": "false",
        "year": 1958,
    }
    assert client.search_movie("Vertigo", year=1958) == expected  # from cache, no HTTP
    assert len(session.calls) == 1


def test_search_cache_keys_differ_by_year_and_are_file_safe(tmp_path):
    client, session = make_client(
        tmp_path, FakeResponse(200, {"results": []}), FakeResponse(200, {"results": []})
    )
    client.search_movie("Oslo, 31 août / ?*")
    client.search_movie("Oslo, 31 août / ?*", year=2011)
    assert len(session.calls) == 2
    names = [f.name for f in (tmp_path / "search").iterdir()]
    assert len(names) == 2 and all(n.replace("_", "").replace(".", "").isalnum() for n in names)


def test_person_search_and_directing_credits(tmp_path):
    people = {"results": [{"id": 7, "name": "Joseph Losey", "known_for_department": "Directing"}]}
    credits = {
        "crew": [
            {"id": 94655, "title": "Eva", "original_title": "Eva", "job": "Director"},
            {"id": 5, "title": "Autre", "job": "Writer"},
        ]
    }
    client, session = make_client(tmp_path, FakeResponse(200, people), FakeResponse(200, credits))
    assert client.search_person("Joseph Losey") == people["results"]
    assert client.person_directing(7) == [
        {"id": 94655, "title": "Eva", "original_title": "Eva", "release_date": None}
    ]
    assert session.calls[1]["url"].endswith("/person/7/movie_credits")
    assert session.calls[1]["params"] == {"language": "fr-FR"}
