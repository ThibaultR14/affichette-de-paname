"""Measure `affichette.matching` on the spike #1 sample (manual tool, not a test).

Replays the 220 distinct SCARE titles of the spike (`spikes/data/scare_titles.json`, local,
not versioned) WITHOUT the source's tmdb id and without overrides, so only the TMDB search is
measured. The SCARE id serves as the reference. Uses the real TMDB client and its cache
(`TMDB_READ_TOKEN` from the repo's `.env`, never printed).

    cd pipeline
    uv run python -m scripts.eval_matching            # --sweep to try other thresholds
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

from dotenv import load_dotenv

from affichette.matching import Matcher, MatchQuery, Thresholds
from affichette.tmdb import Tmdb

ROOT = Path(__file__).resolve().parents[1]
TITLES = ROOT / "spikes" / "data" / "scare_titles.json"
SPIKE = {"matched": 149, "n": 220, "agree": 107, "both": 107}


def sample_titles(rows: list[dict], limit: int) -> list[dict]:
    """Same sample as spikes/tmdb_match_probe.py (Paris first, then a seeded shuffle)."""
    seen: dict[str, dict] = {}
    for r in rows:
        title = (r.get("filmtitle") or "").strip()
        if title and title.casefold() not in seen:
            seen[title.casefold()] = r
    paris = [r for r in seen.values() if str(r.get("cinecp", "")).startswith("75")]
    others = [r for r in seen.values() if not str(r.get("cinecp", "")).startswith("75")]
    random.Random(1).shuffle(others)
    return (paris + others)[:limit]


def evaluate(tmdb: Tmdb, sample: list[dict], thresholds: Thresholds) -> dict:
    matcher = Matcher(tmdb, overrides={}, thresholds=thresholds)
    out = Counter()
    disagreements = []
    for r in sample:
        query = MatchQuery(
            raw_title=r["filmtitle"],
            cinema_id=r.get("cinenom"),
            director_hint=r.get("filmdirector") or None,
            event_label=r.get("evenement") or None,
        )
        m = matcher.match(query)
        ref = r.get("_donnees_imdb.id")
        out["n"] += 1
        out[f"method:{m.method}" if m.tmdb_id else f"none:{m.reason}"] += 1
        if m.tmdb_id:
            out["matched"] += 1
        if ref and m.tmdb_id:
            out["both"] += 1
            if int(ref) == m.tmdb_id:
                out["agree"] += 1
            else:
                disagreements.append((r["filmtitle"], int(ref), m.tmdb_id, m.method))
        if ref and not m.tmdb_id:
            out["ref_missed"] += 1
    return {"counts": out, "disagreements": disagreements, "report": matcher.report}


def line(label: str, c: Counter) -> str:
    return (
        f"{label}: {c['matched']}/{c['n']} = {c['matched'] / c['n']:.1%}, "
        f"accord SCARE {c['agree']}/{c['both']}, id SCARE manqués {c['ref_missed']}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=220)
    parser.add_argument("--sweep", action="store_true")
    parser.add_argument("--report", action="store_true", help="affiche le rapport complet")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv(ROOT.parent / ".env")
    if not TITLES.exists():
        print(f"{TITLES} absent : lance d'abord spikes/tmdb_match_probe.py")
        return 1
    sample = sample_titles(json.loads(TITLES.read_text("utf-8")), args.limit)
    tmdb = Tmdb()

    base = evaluate(tmdb, sample, Thresholds())
    c = base["counts"]
    print(
        f"spike #1: {SPIKE['matched']}/{SPIKE['n']} = {SPIKE['matched'] / SPIKE['n']:.1%}, "
        f"accord SCARE {SPIKE['agree']}/{SPIKE['both']}"
    )
    print(line("matching.py", c))
    print("détail:", dict(sorted((k, v) for k, v in c.items() if ":" in k)))
    for title, ref, got, method in base["disagreements"]:
        print(f"  désaccord: {title!r} SCARE {ref} / nous {got} ({method})")
    if args.report:
        print(base["report"].summary())
    print(f"TMDB : {tmdb.stats['http']} requête(s), {tmdb.stats['cache_hits']} depuis le cache")

    if args.sweep:
        for title_score in (0.85, 0.9, 0.95):
            for director_title in (0.6, 0.7, 0.8):
                t = replace(Thresholds(), title_score=title_score, director_title=director_title)
                c = evaluate(tmdb, sample, t)["counts"]
                print(line(f"title≥{title_score} director_title≥{director_title}", c))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
