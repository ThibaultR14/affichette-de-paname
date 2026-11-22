"""Offline stand-ins for `requests.Session` (no network in tests)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from affichette.db import DbError

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

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        return self._next(method, url, **kwargs)


def connection_error() -> requests.ConnectionError:
    # Real requests errors embed the URL (with query string) in their message.
    return requests.ConnectionError(
        "HTTPSConnectionPool(host='api.themoviedb.org', port=443): Max retries exceeded with "
        "url: /3/movie/426?append_to_response=credits&language=fr-FR"
    )


# --- In-memory PostgREST ------------------------------------------------------------------------

_AND = re.compile(r'(\w+)\.(gte|gt|lte|lt)\."([^"]*)"')
_OPS = {
    "gte": lambda a, b: a >= b,
    "gt": lambda a, b: a > b,
    "lte": lambda a, b: a <= b,
    "lt": lambda a, b: a < b,
}


def _in_values(spec: str) -> list[str]:
    inner = spec[len("in.(") : -1]
    values = []
    for m in re.finditer(r'"((?:[^"\\]|\\.)*)"|([^,]+)', inner):
        quoted, bare = m.groups()
        values.append(re.sub(r"\\(.)", r"\1", quoted) if quoted is not None else bare)
    return values


def _as_time(value: Any) -> datetime:
    return datetime.fromisoformat(value) if isinstance(value, str) else value


def _match(row: dict[str, Any], params: dict[str, str]) -> bool:
    for col, spec in params.items():
        if col in ("select", "order", "limit", "offset"):
            continue
        if col == "and":
            for c, op, value in _AND.findall(spec):
                if row.get(c) is None or not _OPS[op](_as_time(row[c]), _as_time(value)):
                    return False
        elif spec == "is.null":
            if row.get(col) is not None:
                return False
        elif spec.startswith("eq."):
            if str(row.get(col)) != spec[3:]:
                return False
        elif spec.startswith("in.("):
            if str(row.get(col)) not in _in_values(spec):
                return False
        else:
            raise AssertionError(f"filtre non géré : {col}={spec}")
    return True


class FakeDb:
    """Applies the pipeline's PostgREST calls to dicts (only the filters the pipeline uses)."""

    def __init__(self, now: datetime | None = None, **tables: list[dict[str, Any]]):
        self.now = now or datetime(2026, 11, 22, 4, 0, tzinfo=UTC)
        self.tables = {name: [dict(r) for r in rows] for name, rows in tables.items()}
        self.writes: list[tuple[str, str]] = []
        self.fail_on: set[tuple[str, str]] = set()  # (operation, table) -> DbError
        self._ids = 1000

    def _check(self, op: str, table: str) -> None:
        if (op, table) in self.fail_on:
            raise DbError(f"PostgREST 500 sur {table} : panne simulée")

    def _defaults(self, table: str) -> dict[str, Any]:
        self._ids += 1
        if table == "screenings":
            now = self.now.isoformat()
            return {
                "id": self._ids,
                "first_seen_at": now,
                "last_seen_at": now,
                "cancelled_at": None,
            }
        return {"id": self._ids}

    def select(self, table: str, params: dict[str, str]) -> list[dict[str, Any]]:
        self._check("select", table)
        rows = [r for r in self.tables.get(table, []) if _match(r, params)]
        offset, limit = int(params.get("offset", 0)), params.get("limit")
        rows = rows[offset : offset + int(limit)] if limit else rows[offset:]
        cols = params.get("select", "*")
        if cols == "*":
            return [dict(r) for r in rows]
        return [{c: r.get(c) for c in cols.split(",")} for r in rows]

    def upsert(self, table: str, rows: list[dict[str, Any]], on_conflict: str) -> None:
        self._check("upsert", table)
        if not rows:
            return
        self.writes.append(("upsert", table))
        keys = on_conflict.split(",")
        existing = self.tables.setdefault(table, [])
        seen = set()
        for row in rows:
            key = tuple(row.get(k) for k in keys)
            if key in seen:  # like Postgres: "cannot affect row a second time"
                raise DbError(f"PostgREST 500 sur {table} : doublon dans le lot")
            seen.add(key)
            current = next((r for r in existing if tuple(r.get(k) for k in keys) == key), None)
            if current is None:
                existing.append({**self._defaults(table), **row})
            else:
                current.update(row)

    def insert(self, table: str, rows: list[dict[str, Any]]) -> None:
        self._check("insert", table)
        if rows:
            self.writes.append(("insert", table))
            self.tables.setdefault(table, []).extend({**self._defaults(table), **r} for r in rows)

    def update(self, table: str, values: dict[str, Any], filters: dict[str, str]) -> None:
        self._check("update", table)
        self.writes.append(("update", table))
        for row in self.tables.get(table, []):
            if _match(row, filters):
                row.update(values)
