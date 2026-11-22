"""Offline stand-ins for `requests.Session` (no network in tests)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@dataclass
class FakeResponse:
    status_code: int = 200
    body: Any = None
    headers: dict[str, str] = field(default_factory=dict)

    def json(self) -> Any:
        if isinstance(self.body, str):
            raise ValueError("not JSON")  # like requests.JSONDecodeError
        return self.body

    @property
    def text(self) -> str:
        if isinstance(self.body, str):
            return self.body
        return json.dumps(self.body) if self.body is not None else ""


class FakeSession:
    """Returns the queued responses in order (an exception instance is raised instead)."""

    def __init__(self, *responses: FakeResponse | Exception):
        self.responses = list(responses)
        self.headers: dict[str, str] = {}
        self.calls: list[dict[str, Any]] = []

    def _next(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        if not self.responses:
            raise AssertionError("unexpected HTTP call")
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        return self._next("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        return self._next("POST", url, **kwargs)


def connection_error() -> requests.ConnectionError:
    # Real requests errors embed the URL (with query string) in their message.
    return requests.ConnectionError(
        "HTTPSConnectionPool(host='api.themoviedb.org', port=443): Max retries exceeded with "
        "url: /3/movie/426?append_to_response=credits&language=fr-FR"
    )
