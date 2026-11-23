from datetime import UTC, datetime

from affichette.main import CinemaResult, RunReport
from affichette.report import (
    GithubIssues,
    issue_title,
    open_failure_issues,
    open_global_issue,
    run_url,
    write_step_summary,
)
from tests.fakes import FakeResponse, FakeSession, connection_error

NOW = datetime(2026, 11, 23, 4, 0, tzinfo=UTC)
URL = "https://github.com/owner/repo/actions/runs/42"


def report(*failed: str) -> RunReport:
    results = [CinemaResult("champo", "ok", n_screenings=3)]
    results += [CinemaResult(c, "error", error="SCARE : réponse invalide") for c in failed]
    return RunReport(results)


def gh(*responses) -> tuple[GithubIssues, FakeSession]:
    session = FakeSession(*responses)
    return GithubIssues("owner/repo", "ghs_secret", session), session


def issue(number: int, title: str, pr: bool = False) -> dict:
    item = {"number": number, "title": title}
    if pr:
        item["pull_request"] = {}
    return item


def test_step_summary_appended_to_the_actions_file(tmp_path):
    path = tmp_path / "summary.md"
    path.write_text("avant\n", encoding="utf-8")
    write_step_summary("import : 1/1 salle(s) ok", {"GITHUB_STEP_SUMMARY": str(path)})
    text = path.read_text(encoding="utf-8")
    assert text.startswith("avant\n")
    assert "```\nimport : 1/1 salle(s) ok\n```" in text


def test_no_step_summary_outside_actions(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_step_summary("x", {})
    assert list(tmp_path.iterdir()) == []


def test_run_url():
    env = {
        "GITHUB_SERVER_URL": "https://github.com",
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_RUN_ID": "42",
    }
    assert run_url(env) == URL
    assert run_url({}) is None


def test_from_env_needs_repo_and_token():
    assert GithubIssues.from_env({"GITHUB_REPOSITORY": "owner/repo"}) is None
    assert GithubIssues.from_env({"GITHUB_TOKEN": "t"}) is None
    assert GithubIssues.from_env({"GITHUB_REPOSITORY": "o/r", "GITHUB_TOKEN": "t"}) is not None


def test_no_failure_no_http_call():
    client, session = gh()
    assert open_failure_issues(report(), client, NOW, URL) == {}
    assert session.calls == []


def test_failure_opens_one_issue():
    client, session = gh(FakeResponse(200, []), FakeResponse(201, {"number": 7}))
    assert open_failure_issues(report("louxor"), client, NOW, URL) == {"louxor": 7}
    get, post = session.calls
    assert get["method"] == "GET"
    assert get["url"] == "https://api.github.com/repos/owner/repo/issues"
    assert get["params"]["state"] == "open"
    assert post["method"] == "POST"
    payload = post["json"]
    assert payload["title"] == "import en échec : louxor"
    assert payload["labels"] == ["import"]
    assert "SCARE : réponse invalide" in payload["body"]
    assert "2026-11-23 05:00" in payload["body"]  # Paris time
    assert URL in payload["body"]
    assert session.headers["Authorization"] == "Bearer ghs_secret"
    assert "ghs_secret" not in payload["body"]


def test_already_open_issue_is_not_duplicated():
    open_issues = [issue(3, issue_title("louxor")), issue(4, issue_title("champo"), pr=True)]
    client, session = gh(FakeResponse(200, open_issues), FakeResponse(201, {"number": 8}))
    assert open_failure_issues(report("louxor", "champo"), client, NOW) == {
        "louxor": 3,
        "champo": 8,  # a pull request with that title does not count
    }
    posts = [c for c in session.calls if c["method"] == "POST"]
    assert [p["json"]["title"] for p in posts] == ["import en échec : champo"]


def test_open_issues_are_paginated():
    page1 = [issue(100 + i, f"autre {i}") for i in range(100)]
    page2 = [issue(5, issue_title("louxor"))]
    client, session = gh(FakeResponse(200, page1), FakeResponse(200, page2))
    assert open_failure_issues(report("louxor"), client, NOW) == {"louxor": 5}
    assert [c["params"]["page"] for c in session.calls] == ["1", "2"]


def test_github_error_is_logged_not_raised(caplog):
    client, _ = gh(FakeResponse(403, {"message": "Resource not accessible"}))
    assert open_failure_issues(report("louxor"), client, NOW) == {}
    assert "GitHub 403" in caplog.text


def test_unexpected_github_responses_are_logged_not_raised(caplog):
    client, _ = gh(FakeResponse(200, "<html>proxy</html>"))
    assert open_failure_issues(report("louxor"), client, NOW) == {}
    assert "réponse non JSON" in caplog.text
    client, _ = gh(FakeResponse(200, []), FakeResponse(201, {"id": 1}))
    assert open_failure_issues(report("louxor"), client, NOW) == {}
    assert "numéro d'issue absent" in caplog.text


def test_step_summary_write_error_is_logged(tmp_path, caplog):
    write_step_summary("x", {"GITHUB_STEP_SUMMARY": str(tmp_path / "absent" / "s.md")})
    assert "résumé du job non écrit (FileNotFoundError)" in caplog.text


def test_global_issue():
    client, session = gh(FakeResponse(200, []), FakeResponse(201, {"number": 9}))
    assert open_global_issue("SUPABASE_URL manquant", client, NOW, URL) == {"global": 9}
    payload = session.calls[1]["json"]
    assert payload["title"] == "import en échec : global"
    assert "L'import entier a échoué" in payload["body"]
    assert "SUPABASE_URL manquant" in payload["body"]


def test_github_unreachable_is_logged_without_url(caplog):
    client, _ = gh(connection_error())
    assert open_failure_issues(report("louxor"), client, NOW) == {}
    assert "GitHub injoignable (ConnectionError)" in caplog.text
    assert "api." not in caplog.text
