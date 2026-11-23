"""Import report for GitHub Actions: job summary, and one issue per failing cinema.

- `write_step_summary` appends the report to `$GITHUB_STEP_SUMMARY` (the run's summary page).
- `open_global_issue` opens `import en échec : global` when the whole run fails (exit code 2,
  except a bad `--cinema`).
- `open_failure_issues` opens `import en échec : <cinema_id>` unless an open issue already has
  that exact title (no duplicate, no comment). Closing it once the cinema recovers is manual.

Nothing happens outside Actions (no `GITHUB_TOKEN` / `GITHUB_REPOSITORY`). A GitHub failure is
logged and never stops the import nor changes its exit code. The token is sent in headers only
and never logged.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

import requests

if TYPE_CHECKING:
    from affichette.main import RunReport

log = logging.getLogger(__name__)

API = "https://api.github.com"
TIMEOUT_S = 30
LABEL = "import"
PER_PAGE = 100
MAX_PAGES = 10
PARIS = ZoneInfo("Europe/Paris")
GLOBAL = "global"  # issue subject when the whole run fails


class GithubError(RuntimeError):
    """GitHub API call failed. The message never contains the token."""


def issue_title(cinema_id: str) -> str:
    return f"import en échec : {cinema_id}"


def write_step_summary(text: str, env: Mapping[str, str]) -> None:
    """Append `text` as a code block to the Actions job summary, if there is one."""
    path = env.get("GITHUB_STEP_SUMMARY", "").strip()
    if not path:
        return
    try:
        with Path(path).open("a", encoding="utf-8") as f:
            f.write(f"## Import des séances\n\n```\n{text}\n```\n")
    except OSError as exc:
        log.error("résumé du job non écrit (%s)", type(exc).__name__)


def run_url(env: Mapping[str, str]) -> str | None:
    server, repo, run_id = (
        env.get(k, "").strip() for k in ("GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_RUN_ID")
    )
    return f"{server}/{repo}/actions/runs/{run_id}" if server and repo and run_id else None


class GithubIssues:
    def __init__(self, repo: str, token: str, session: requests.Session | None = None):
        self.base = f"{API}/repos/{repo}/issues"
        self.session = session or requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"
        self.session.headers["Accept"] = "application/vnd.github+json"
        self.session.headers["X-GitHub-Api-Version"] = "2022-11-28"

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> GithubIssues | None:
        repo = env.get("GITHUB_REPOSITORY", "").strip()
        token = env.get("GITHUB_TOKEN", "").strip()
        return cls(repo, token) if repo and token else None

    def _request(self, method: str, **kwargs: Any) -> Any:
        try:
            r = self.session.request(method, self.base, timeout=TIMEOUT_S, **kwargs)
        except requests.RequestException as exc:
            raise GithubError(f"GitHub injoignable ({type(exc).__name__})") from None
        if r.status_code >= 300:
            raise GithubError(f"GitHub {r.status_code} : {r.text[:300]}")
        try:
            return r.json()
        except ValueError:
            raise GithubError(f"GitHub {r.status_code} : réponse non JSON") from None

    def open_titles(self) -> dict[str, int]:
        """Open issues (pull requests excluded): title -> number."""
        titles: dict[str, int] = {}
        for page in range(1, MAX_PAGES + 1):
            params = {"state": "open", "per_page": str(PER_PAGE), "page": str(page)}
            items = self._request("GET", params=params)
            if not isinstance(items, list):
                raise GithubError("GitHub : liste d'issues attendue")
            for item in items:
                if isinstance(item, dict) and "pull_request" not in item and "title" in item:
                    titles.setdefault(item["title"], item.get("number", 0))
            if len(items) < PER_PAGE:
                break
        return titles

    def create(self, title: str, body: str) -> int:
        created = self._request("POST", json={"title": title, "body": body, "labels": [LABEL]})
        if not isinstance(created, dict) or "number" not in created:
            raise GithubError("GitHub : numéro d'issue absent de la réponse")
        return created["number"]


def issue_body(cinema_id: str, error: str | None, now: datetime, url: str | None) -> str:
    when = now.astimezone(PARIS).strftime("%Y-%m-%d %H:%M")
    if cinema_id == GLOBAL:
        head = [
            f"L'import entier a échoué le {when} (heure de Paris), avant toute salle.",
            "Aucune salle n'a été mise à jour.",
        ]
    else:
        head = [
            f"L'import de **{cinema_id}** a échoué le {when} (heure de Paris).",
            "Ses dernières séances connues restent affichées.",
        ]
    lines = [
        *head,
        "",
        "```",
        error or "erreur inconnue",
        "```",
    ]
    if url:
        lines += ["", f"Run : {url}"]
    lines += [
        "",
        "Aucune autre issue ne sera ouverte pour cette salle tant que celle-ci reste ouverte."
        " À fermer à la main quand l'import repasse.",
    ]
    return "\n".join(lines)


def open_issues(
    failures: list[tuple[str, str | None]], gh: GithubIssues, now: datetime, url: str | None
) -> dict[str, int]:
    """One issue per `(subject, error)`, none if already open. Returns subject -> issue number."""
    if not failures:
        return {}
    issues: dict[str, int] = {}
    try:
        open_titles = gh.open_titles()
        for subject, error in failures:
            title = issue_title(subject)
            if title in open_titles:
                log.info("%s : issue #%d déjà ouverte", subject, open_titles[title])
                issues[subject] = open_titles[title]
                continue
            number = gh.create(title, issue_body(subject, error, now, url))
            log.info("%s : issue #%d ouverte", subject, number)
            issues[subject] = number
    except GithubError as exc:
        log.error("issue d'échec non ouverte : %s", exc)
    return issues


def open_failure_issues(
    report: RunReport, gh: GithubIssues, now: datetime, url: str | None = None
) -> dict[str, int]:
    """One issue per failing cinema."""
    return open_issues([(r.cinema_id, r.error) for r in report.failed], gh, now, url)


def open_global_issue(
    error: str, gh: GithubIssues, now: datetime, url: str | None = None
) -> dict[str, int]:
    """The whole run failed before any cinema (configuration, Supabase or TMDB down)."""
    return open_issues([(GLOBAL, error)], gh, now, url)
