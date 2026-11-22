"""Spike #1 - throwaway probe of the SCARE open dataset (data.gouv.fr).

Dataset: "Programmation des cinémas indépendants" (Licence Ouverte 2.0), served by a
data-fair API at datacinesindes.fr. Downloads Paris lines and prints coverage per cinema.

Usage: uv run python spikes/datagouv_probe.py [--offline]
Not tested, not imported by the pipeline.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

API = "https://datacinesindes.fr/data-fair/api/v1/datasets/programmation-cinemas"
DATA = Path(__file__).parent / "data"
PARIS = ZoneInfo("Europe/Paris")
UA = {"User-Agent": "affichette-spike/0.1"}


def fetch() -> list[dict]:
    rows: list[dict] = []
    url = f"{API}/lines"
    params = {"qs": "cinecp:75*", "size": 1000, "sort": "showstart"}
    while url:
        resp = requests.get(url, params=params, headers=UA, timeout=30)
        resp.raise_for_status()
        body = resp.json()
        rows.extend(body["results"])
        url, params = body.get("next"), None
    DATA.mkdir(exist_ok=True)
    (DATA / "datagouv_paris.json").write_text(json.dumps(rows, ensure_ascii=False), "utf-8")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    cached = DATA / "datagouv_paris.json"
    rows = json.loads(cached.read_text("utf-8")) if args.offline else fetch()

    today = datetime.now(PARIS).replace(hour=0, minute=0, second=0, microsecond=0)
    horizon = today + timedelta(days=7)
    by_cinema: dict[str, list[dict]] = collections.defaultdict(list)
    for row in rows:
        by_cinema[row["cinenom"]].append(row)

    print(f"{len(rows)} lignes Paris, aujourd'hui = {today:%Y-%m-%d}")
    fields = ("filmversion", "filmaudio", "showurl", "filmdirector", "filmduration")
    for name, shows in sorted(by_cinema.items(), key=lambda kv: -len(kv[1])):
        starts = sorted(datetime.fromisoformat(s["showstart"]) for s in shows if s.get("showstart"))
        if not starts:
            print(f"{name:32} n={len(shows):3} (sans showstart)")
            continue
        upcoming = [s for s in starts if today <= s < horizon]
        last_day = max(starts).astimezone(PARIS).date()
        filled = {f: sum(1 for s in shows if s.get(f)) for f in fields}
        tmdb = sum(1 for s in shows if s.get("_donnees_imdb.id"))
        print(
            f"{name:32} n={len(shows):3} 7j={len(upcoming):3} "
            f"{starts[0]:%m-%d}->{last_day:%m-%d} tmdb={tmdb} "
            + " ".join(f"{k}={v}" for k, v in filled.items())
        )
    versions = collections.Counter((s.get("filmversion"), s.get("filmaudio")) for s in rows)
    print("versions:", versions.most_common(10))


if __name__ == "__main__":
    sys.exit(main())
