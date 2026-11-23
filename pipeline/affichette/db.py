"""Minimal Supabase (PostgREST) client for the pipeline, with the `service_role` key.

Plain `requests` on `/rest/v1/<table>`: the pipeline only needs a few selects, upserts, inserts
and updates, which does not justify the `supabase` package. The key is sent in headers only and
never logged.
"""

from __future__ import annotations

import os
from typing import Any

import requests

TIMEOUT_S = 30


class DbError(RuntimeError):
    """PostgREST call failed. The message never contains the key."""


def in_list(values: list[str]) -> str:
    """PostgREST `in.(...)` filter, values double-quoted (they may contain `:` or `,`)."""
    quoted = ",".join('"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"' for v in values)
    return f"in.({quoted})"


class Db:
    def __init__(self, url: str, key: str, session: requests.Session | None = None):
        if not url or not key:
            raise DbError("SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY manquant")
        self.rest = url.rstrip("/") + "/rest/v1"
        self.session = session or requests.Session()
        self.session.headers["apikey"] = key
        self.session.headers["Authorization"] = f"Bearer {key}"

    @classmethod
    def from_env(cls) -> Db:
        return cls(
            os.environ.get("SUPABASE_URL", "").strip(),
            os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip(),
        )

    def _request(self, method: str, table: str, **kwargs: Any) -> requests.Response:
        try:
            r = self.session.request(method, f"{self.rest}/{table}", timeout=TIMEOUT_S, **kwargs)
        except requests.RequestException as exc:
            raise DbError(f"Supabase injoignable ({type(exc).__name__}) sur {table}") from None
        if r.status_code >= 300:
            raise DbError(f"PostgREST {r.status_code} sur {table} : {r.text[:500]}")
        return r

    def select(self, table: str, params: dict[str, str]) -> list[dict[str, Any]]:
        """GET rows with PostgREST query params (`select`, `col=eq.x`…)."""
        return self._request("GET", table, params=params).json()

    def upsert(self, table: str, rows: list[dict[str, Any]], on_conflict: str) -> None:
        """Insert or update `rows` on the `on_conflict` columns (all rows: same keys).

        On conflict, only the columns sent are updated: a column left out (`first_seen_at`)
        keeps its value.
        """
        if not rows:
            return
        self._request(
            "POST",
            table,
            params={"on_conflict": on_conflict},
            json=rows,
            headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        )

    def insert(self, table: str, rows: list[dict[str, Any]]) -> None:
        """Plain INSERT (all rows: same keys)."""
        if not rows:
            return
        self._request("POST", table, json=rows, headers={"Prefer": "return=minimal"})

    def update(self, table: str, values: dict[str, Any], filters: dict[str, str]) -> None:
        """PATCH `values` on the rows matching `filters` (PostgREST syntax). Filters required."""
        if not filters:
            raise DbError(f"update sans filtre sur {table} refusé")
        self._request(
            "PATCH", table, params=filters, json=values, headers={"Prefer": "return=minimal"}
        )


class DryRunDb:
    """Reads go to the real database, writes are only recorded (`--dry-run`)."""

    def __init__(self, db: Any):
        self.db = db
        self.writes: list[tuple[str, str, Any]] = []  # (operation, table, payload)

    def select(self, table: str, params: dict[str, str]) -> list[dict[str, Any]]:
        return self.db.select(table, params)

    def upsert(self, table: str, rows: list[dict[str, Any]], on_conflict: str) -> None:
        if rows:
            self.writes.append(("upsert", table, rows))

    def insert(self, table: str, rows: list[dict[str, Any]]) -> None:
        if rows:
            self.writes.append(("insert", table, rows))

    def update(self, table: str, values: dict[str, Any], filters: dict[str, str]) -> None:
        self.writes.append(("update", table, {"values": values, "filters": filters}))

    def summary(self) -> str:
        counts: dict[tuple[str, str], int] = {}
        for op, table, payload in self.writes:
            n = len(payload) if isinstance(payload, list) else 1
            counts[(op, table)] = counts.get((op, table), 0) + n
        if not counts:
            return "dry-run : aucune écriture prévue"
        return "dry-run, rien n'a été écrit. Écritures prévues : " + ", ".join(
            f"{op} {table} ×{n}" for (op, table), n in sorted(counts.items())
        )
