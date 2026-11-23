from datetime import UTC, datetime, timedelta

import pytest
import requests

from affichette import main as main_mod
from affichette.db import DryRunDb
from affichette.main import UsageError, error_message, run
from affichette.matching import DbTitleMatchStore, Matcher
from affichette.sources import SourceError
from affichette.sources.scare import ScareSource
from affichette.tmdb import Cached
from tests.fakes import FakeDb, FakeResponse, FakeSession, fixture

NOW = datetime(2026, 11, 22, 4, 0, tzinfo=UTC)

SCARE_CINEMAS = {
    "champo": "Le Champo",
    "saint-andre-des-arts": "Saint-André des Arts",
    "grand-action": "Le Grand Action",
    "louxor": "Le Louxor - Palais du cinéma",
    "epee-de-bois": "Epée de bois",
    "sept-parnassiens": "Sept Parnassiens",
}
# Screenings of the fixture inside [22/11, 29/11[ (Paris), per cinema.
EXPECTED = {
    "champo": 3,
    "saint-andre-des-arts": 2,
    "grand-action": 1,
    "louxor": 1,
    "epee-de-bois": 1,
    "sept-parnassiens": 1,
}


def cinemas() -> list[dict]:
    rows = [
        {"id": cid, "name": cid, "source": "scare", "source_ref": ref}
        for cid, ref in SCARE_CINEMAS.items()
    ]
    rows.append({"id": "reflet-medicis", "name": "Reflet", "source": "dulac", "source_ref": "583"})
    rows.append({"id": "christine", "name": "Christine", "source": "none", "source_ref": None})
    return rows


class FakeTmdb:
    """Known movies by id (others: 404). Searches find nothing."""

    def __init__(self, known=(274, 1417, 1318864)):
        self.known = set(known)
        self.calls: list = []
        self.stats = {"http": 0, "cache_hits": 0}

    def movie(self, tmdb_id):
        self.calls.append(("movie", tmdb_id))
        if tmdb_id not in self.known:
            return Cached(None, NOW)
        data = {
            "id": tmdb_id,
            "title": f"Film {tmdb_id}",
            "release_date": "1991-02-14",
            "runtime": 118,
            "directors": ["Someone"],
        }
        return Cached(data, NOW - timedelta(days=2))

    def search_movie(self, query, year=None):
        self.calls.append(("search", query))
        return []

    def search_person(self, name):
        return []

    def person_directing(self, person_id):
        return []


def scare_pages() -> ScareSource:
    return ScareSource(
        FakeSession(
            FakeResponse(200, fixture("scare/page1.json")),
            FakeResponse(200, fixture("scare/page2.json")),
        )
    )


def do_run(db, tmdb=None, source=None, only=None, now=NOW):
    tmdb = tmdb or FakeTmdb()
    matcher = Matcher(tmdb, overrides={}, store=DbTitleMatchStore(db), now=now)
    return run(db, tmdb, {"scare": source or scare_pages()}, matcher, now, only, clock=lambda: now)


def by_key(db):
    return {r["source_key"]: r for r in db.tables.get("screenings", [])}


def test_full_import_writes_every_scare_cinema():
    db = FakeDb(now=NOW, cinemas=cinemas())
    report = do_run(db)
    assert [r.cinema_id for r in report.results] == list(SCARE_CINEMAS)  # no dulac, no none
    assert not report.failed
    assert {r.cinema_id: r.n_screenings for r in report.results} == EXPECTED
    rows = by_key(db)
    assert len(rows) == sum(EXPECTED.values())
    assert rows["scare:champo:34466"]["tmdb_id"] == 274
    assert rows["scare:grand-action:39218"]["version"] == "VF"
    # TMDB id given by SCARE but unknown to TMDB: no film row, so no foreign key.
    assert rows["scare:saint-andre-des-arts:48032"]["tmdb_id"] is None
    assert {f["tmdb_id"] for f in db.tables["films"]} == {274, 1417, 1318864}
    runs = db.tables["import_runs"]
    assert [(r["cinema_id"], r["status"]) for r in runs] == [(c, "ok") for c in SCARE_CINEMAS]
    champo_run = next(r for r in runs if r["cinema_id"] == "champo")
    assert (champo_run["n_screenings"], champo_run["n_unmatched"]) == (3, 1)
    assert champo_run["started_at"] == NOW.isoformat()
    # Titles searched on TMDB are cached in title_matches, one upsert at the end.
    assert {r["normalized_title"] for r in db.tables["title_matches"]} >= {"le troisieme homme"}
    states = {c["id"]: c for c in db.tables["cinemas"]}
    assert states["champo"]["coverage_until"] == "2026-11-28"
    assert states["champo"]["last_import_ok"] is True
    assert "last_import_at" not in states["reflet-medicis"]


def test_rerun_is_idempotent():
    db = FakeDb(now=NOW, cinemas=cinemas())
    do_run(db)
    first = {k: dict(v) for k, v in by_key(db).items()}
    tmdb = FakeTmdb()
    report = do_run(db, tmdb=tmdb)
    assert by_key(db) == first
    assert all(r.n_cancelled == 0 for r in report.results)
    assert not [c for c in tmdb.calls if c[0] == "search"]  # title_matches cache reused
    assert {c[1] for c in tmdb.calls if c[0] == "movie"} == {1496491}  # only the 404 again


def test_stale_film_is_refreshed_fresh_one_is_not():
    films = [
        {"tmdb_id": 274, "tmdb_fetched_at": (NOW - timedelta(days=3)).isoformat()},
        {"tmdb_id": 1417, "tmdb_fetched_at": (NOW - timedelta(days=40)).isoformat()},
    ]
    db = FakeDb(now=NOW, cinemas=cinemas(), films=films)
    tmdb = FakeTmdb()
    do_run(db, tmdb=tmdb, only=["champo"])
    fetched = {c[1] for c in tmdb.calls if c[0] == "movie"}
    assert 274 not in fetched
    assert 1417 in fetched


def test_film_unknown_to_tmdb_but_already_in_films_is_kept():
    films = [{"tmdb_id": 274, "tmdb_fetched_at": (NOW - timedelta(days=40)).isoformat()}]
    db = FakeDb(now=NOW, cinemas=cinemas(), films=films)
    do_run(db, tmdb=FakeTmdb(known=()), only=["champo"])
    assert by_key(db)["scare:champo:34466"]["tmdb_id"] == 274


class FailingFor:
    """Wraps a source and fails for some cinemas."""

    def __init__(self, inner, failing):
        self.inner, self.failing = inner, failing

    def fetch(self, cinema, start, end):
        if cinema.id in self.failing:
            raise SourceError(f"{cinema.id} : source en panne")
        return self.inner.fetch(cinema, start, end)


def test_failed_cinema_is_left_untouched_others_continue():
    db = FakeDb(now=NOW, cinemas=cinemas())
    do_run(db)
    louxor_before = {k: dict(v) for k, v in by_key(db).items() if ":louxor:" in k}
    later = NOW + timedelta(hours=6)
    db.now = later
    report = do_run(db, source=FailingFor(scare_pages(), {"louxor"}), now=later)
    assert [r.cinema_id for r in report.failed] == ["louxor"]
    assert report.failed[0].error == "louxor : source en panne"
    assert {k: v for k, v in by_key(db).items() if ":louxor:" in k} == louxor_before
    states = {c["id"]: c for c in db.tables["cinemas"]}
    assert states["louxor"]["last_import_ok"] is False
    assert states["louxor"]["coverage_until"] == "2026-11-22"  # kept
    assert states["louxor"]["last_success_at"] == NOW.isoformat()  # kept
    assert states["louxor"]["last_import_at"] == later.isoformat()
    assert states["champo"]["last_success_at"] == later.isoformat()
    assert states["champo"]["last_import_ok"] is True
    last = db.tables["import_runs"][-len(SCARE_CINEMAS) :]
    louxor_run = next(r for r in last if r["cinema_id"] == "louxor")
    assert (louxor_run["status"], louxor_run["error"]) == ("error", "louxor : source en panne")
    assert "ÉCHEC" in report.summary()


def test_empty_scare_fails_every_cinema_and_cancels_nothing():
    db = FakeDb(now=NOW, cinemas=cinemas())
    do_run(db)
    empty = ScareSource(FakeSession(FakeResponse(200, {"total": 0, "results": []})))
    report = do_run(db, source=empty)
    assert len(report.failed) == len(SCARE_CINEMAS)
    assert all(r["cancelled_at"] is None for r in db.tables["screenings"])


def test_vanished_screening_is_cancelled_on_next_import():
    db = FakeDb(now=NOW, cinemas=cinemas())
    do_run(db)
    page1, page2 = fixture("scare/page1.json"), fixture("scare/page2.json")
    page1["results"] = [r for r in page1["results"] if r["showid"] != "34717"]
    source = ScareSource(FakeSession(FakeResponse(200, page1), FakeResponse(200, page2)))
    report = do_run(db, source=source)
    champo = next(r for r in report.results if r.cinema_id == "champo")
    assert champo.n_cancelled == 1
    assert by_key(db)["scare:champo:34717"]["cancelled_at"] == NOW.isoformat()


def test_database_error_is_isolated_per_cinema():
    db = FakeDb(now=NOW, cinemas=cinemas())
    db.fail_on.add(("upsert", "screenings"))
    report = do_run(db)
    assert len(report.failed) == len(SCARE_CINEMAS)
    assert "panne simulée" in report.failed[0].error
    assert len(db.tables["import_runs"]) == len(SCARE_CINEMAS)


def test_dry_run_writes_nothing():
    db = FakeDb(now=NOW, cinemas=cinemas())
    dry = DryRunDb(db)
    report = do_run(dry)
    assert not report.failed
    assert db.writes == []
    assert "screenings" not in db.tables
    tables = {table for _, table, _ in dry.writes}
    assert tables == {"films", "screenings", "cinemas", "import_runs", "title_matches"}
    assert "rien n'a été écrit" in dry.summary()


def test_only_one_cinema():
    db = FakeDb(now=NOW, cinemas=cinemas())
    report = do_run(db, only=["champo", "champo"])
    assert [r.cinema_id for r in report.results] == ["champo"]
    assert {r["cinema_id"] for r in db.tables["screenings"]} == {"champo"}


@pytest.mark.parametrize(
    ("cinema", "message"),
    [("inconnue", "salle inconnue"), ("reflet-medicis", "pas de source importable")],
)
def test_bad_cinema_option(cinema, message):
    db = FakeDb(now=NOW, cinemas=cinemas())
    with pytest.raises(UsageError, match=message):
        do_run(db, only=[cinema])
    assert db.writes == []


def test_error_message_never_copies_a_requests_error():
    exc = requests.ConnectionError("Max retries exceeded with url: /3/movie/1?api_key=secret")
    assert error_message(exc) == "ConnectionError"
    assert error_message(KeyError("showid")) == "KeyError: 'showid'"


@pytest.fixture
def cli(monkeypatch):
    """`main()` wired to fakes: no .env, no network."""
    db = FakeDb(now=NOW, cinemas=cinemas())
    source = {"factory": scare_pages}
    monkeypatch.setattr(main_mod, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(main_mod.Db, "from_env", classmethod(lambda cls: db))
    monkeypatch.setattr(main_mod, "Tmdb", FakeTmdb)
    monkeypatch.setattr(main_mod, "ScareSource", lambda: source["factory"]())
    monkeypatch.setattr(main_mod, "_now", lambda: NOW)
    for var in ("GITHUB_TOKEN", "GITHUB_REPOSITORY", "GITHUB_STEP_SUMMARY"):
        monkeypatch.delenv(var, raising=False)
    return db, source


def test_cli_ok(cli, capsys):
    db, _ = cli
    assert main_mod.main(["--cinema", "champo"]) == 0
    out = capsys.readouterr().out
    assert "import : 1/1 salle(s) ok" in out
    assert "correspondance TMDB" in out
    assert len(db.tables["screenings"]) == 3


def test_cli_dry_run(cli, capsys):
    db, _ = cli
    assert main_mod.main(["--dry-run"]) == 0
    assert db.writes == []
    assert "dry-run" in capsys.readouterr().out


def test_cli_exit_1_when_a_cinema_fails(cli):
    _, source = cli
    source["factory"] = lambda: FailingFor(scare_pages(), {"champo"})
    assert main_mod.main([]) == 1


def test_cli_exit_2_on_unknown_cinema(cli):
    assert main_mod.main(["--cinema", "inconnue"]) == 2


class FakeIssues:
    def __init__(self, open_titles=None):
        self.titles = dict(open_titles or {})
        self.created: list[tuple[str, str]] = []

    def open_titles(self):
        return self.titles

    def create(self, title, body):
        self.created.append((title, body))
        return 99


def github_env(monkeypatch, tmp_path, issues):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setattr(main_mod.GithubIssues, "from_env", classmethod(lambda cls, env: issues))
    return summary


def test_cli_in_actions_writes_summary_and_opens_issue(cli, monkeypatch, tmp_path):
    _, source = cli
    source["factory"] = lambda: FailingFor(scare_pages(), {"champo"})
    issues = FakeIssues()
    summary = github_env(monkeypatch, tmp_path, issues)
    assert main_mod.main([]) == 1
    assert "champo : ÉCHEC" in summary.read_text(encoding="utf-8")
    assert [t for t, _ in issues.created] == ["import en échec : champo"]


def test_cli_dry_run_opens_no_issue(cli, monkeypatch, tmp_path):
    _, source = cli
    source["factory"] = lambda: FailingFor(scare_pages(), {"champo"})
    issues = FakeIssues()
    summary = github_env(monkeypatch, tmp_path, issues)
    assert main_mod.main(["--dry-run"]) == 1
    assert summary.exists()
    assert issues.created == []


def test_cli_whole_run_failure_opens_global_issue(cli, monkeypatch, tmp_path):
    db, _ = cli
    db.fail_on.add(("select", "cinemas"))
    issues = FakeIssues()
    summary = github_env(monkeypatch, tmp_path, issues)
    assert main_mod.main([]) == 2
    assert "global" in summary.read_text(encoding="utf-8")
    assert [t for t, _ in issues.created] == ["import en échec : global"]


def test_cli_unknown_cinema_opens_no_issue(cli, monkeypatch, tmp_path):
    issues = FakeIssues()
    github_env(monkeypatch, tmp_path, issues)
    assert main_mod.main(["--cinema", "inconnue"]) == 2
    assert issues.created == []
