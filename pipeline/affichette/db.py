"""Minimal Supabase (PostgREST) writer for the pipeline, with the `service_role` key.

Plain `requests` on `/rest/v1/<table>`: the pipeline only needs upserts, which does not justify
the `supabase` package. The key is sent in headers only and never logged.
"""

from __future__ import annotations

import os
from typing import Any

import requests

TIMEOUT_S = 30


class DbError(RuntimeError):
    """PostgREST call failed. The message never contains the key."""


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

    def upsert(self, table: str, rows: list[dict[str, Any]], on_conflict: str) -> None:
        """Insert or update `rows` on the `on_conflict` columns (all rows: same keys)."""
        if not rows:
            return
        try:
            r = self.session.post(
                f"{self.rest}/{table}",
                params={"on_conflict": on_conflict},
                json=rows,
                headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
                timeout=TIMEOUT_S,
            )
        except requests.RequestException as exc:
            raise DbError(f"Supabase injoignable ({type(exc).__name__}) sur {table}") from None
        if r.status_code >= 300:
            raise DbError(f"PostgREST {r.status_code} sur {table} : {r.text[:500]}")
