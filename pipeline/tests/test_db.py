import pytest

from affichette.db import Db, DbError, DryRunDb, in_list
from tests.fakes import FakeResponse, FakeSession, connection_error

KEY = "service-role-secret"


def test_upsert_posts_rows_with_merge_duplicates():
    session = FakeSession(FakeResponse(201))
    db = Db("https://abc.supabase.co/", KEY, session=session)
    db.upsert("films", [{"tmdb_id": 1, "title": "A"}], on_conflict="tmdb_id")
    (call,) = session.calls
    assert call["method"] == "POST"
    assert call["url"] == "https://abc.supabase.co/rest/v1/films"
    assert call["params"] == {"on_conflict": "tmdb_id"}
    assert call["json"] == [{"tmdb_id": 1, "title": "A"}]
    assert call["headers"]["Prefer"] == "resolution=merge-duplicates,return=minimal"
    assert session.headers["apikey"] == KEY
    assert session.headers["Authorization"] == f"Bearer {KEY}"


def test_upsert_without_rows_does_nothing():
    session = FakeSession()
    Db("https://abc.supabase.co", KEY, session=session).upsert("films", [], "tmdb_id")
    assert session.calls == []


def test_postgrest_error_raises_without_key():
    session = FakeSession(FakeResponse(400, {"message": "null value in column title"}))
    db = Db("https://abc.supabase.co", KEY, session=session)
    with pytest.raises(DbError, match="PostgREST 400 sur films.*null value") as err:
        db.upsert("films", [{"tmdb_id": 1}], "tmdb_id")
    assert KEY not in str(err.value)


def test_network_error_raises_without_url():
    db = Db("https://abc.supabase.co", KEY, session=FakeSession(connection_error()))
    with pytest.raises(DbError) as err:
        db.upsert("films", [{"tmdb_id": 1}], "tmdb_id")
    assert "ConnectionError" in str(err.value)
    assert err.value.__cause__ is None


def test_from_env_requires_both_variables(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    with pytest.raises(DbError, match="SUPABASE_SERVICE_ROLE_KEY"):
        Db.from_env()


def test_select_gets_rows_with_params():
    session = FakeSession(FakeResponse(200, [{"tmdb_id": 1}]))
    db = Db("https://abc.supabase.co", KEY, session=session)
    rows = db.select("title_matches", {"select": "tmdb_id", "cinema_id": "eq.champo"})
    assert rows == [{"tmdb_id": 1}]
    (call,) = session.calls
    assert call["method"] == "GET"
    assert call["url"] == "https://abc.supabase.co/rest/v1/title_matches"
    assert call["params"] == {"select": "tmdb_id", "cinema_id": "eq.champo"}


def test_select_error_raises_without_key():
    session = FakeSession(FakeResponse(401, {"message": "bad jwt"}))
    db = Db("https://abc.supabase.co", KEY, session=session)
    with pytest.raises(DbError, match="PostgREST 401 sur title_matches") as err:
        db.select("title_matches", {})
    assert KEY not in str(err.value)


def test_insert_posts_rows():
    session = FakeSession(FakeResponse(201))
    Db("https://abc.supabase.co", KEY, session=session).insert("import_runs", [{"status": "ok"}])
    (call,) = session.calls
    assert (call["method"], call["url"]) == ("POST", "https://abc.supabase.co/rest/v1/import_runs")
    assert call["json"] == [{"status": "ok"}]
    assert call["headers"]["Prefer"] == "return=minimal"
    assert "params" not in call  # no on_conflict: a plain insert


def test_update_patches_with_filters():
    session = FakeSession(FakeResponse(204))
    db = Db("https://abc.supabase.co", KEY, session=session)
    db.update("cinemas", {"last_import_ok": True}, {"id": "eq.champo"})
    (call,) = session.calls
    assert call["method"] == "PATCH"
    assert call["params"] == {"id": "eq.champo"}
    assert call["json"] == {"last_import_ok": True}


def test_update_without_filter_is_refused():
    db = Db("https://abc.supabase.co", KEY, session=FakeSession())
    with pytest.raises(DbError, match="sans filtre"):
        db.update("screenings", {"cancelled_at": None}, {})


def test_in_list_quotes_values():
    assert in_list(["scare:champo:1", 'a"b,c']) == 'in.("scare:champo:1","a\\"b,c")'


def test_dry_run_db_reads_but_never_writes():
    session = FakeSession(FakeResponse(200, [{"id": "champo"}]))
    dry = DryRunDb(Db("https://abc.supabase.co", KEY, session=session))
    assert dry.select("cinemas", {"select": "id"}) == [{"id": "champo"}]
    dry.upsert("screenings", [{"source_key": "a"}, {"source_key": "b"}], "source_key")
    dry.insert("import_runs", [{"status": "ok"}])
    dry.update("cinemas", {"last_import_ok": True}, {"id": "eq.champo"})
    dry.upsert("films", [], "tmdb_id")
    assert len(session.calls) == 1  # the select only
    assert dry.summary() == (
        "dry-run, rien n'a été écrit. Écritures prévues : insert import_runs ×1, "
        "update cinemas ×1, upsert screenings ×2"
    )
    assert DryRunDb(None).summary() == "dry-run : aucune écriture prévue"
