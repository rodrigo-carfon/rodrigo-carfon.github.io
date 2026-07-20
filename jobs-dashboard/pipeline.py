# -*- coding: utf-8 -*-
"""Job-market ETL — orchestrator.

Fetches every source in the registry with per-source isolation (one flaky portal
never aborts the run), then (later steps) classifies, stores to SQLite and exports
the served JSON snapshot.

Usage:
  python pipeline.py --dry-run     # fetch only, print per-source counts + a sample
  python pipeline.py               # full run (storage/export — added in a later step)
"""
import sys
import os
import time
import argparse
from collections import Counter
from pathlib import Path

from sources import REGISTRY
import classify
import storage

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).parent
DB_PATH = HERE / "data" / "jobs.db"
JSON_PATH = HERE.parent / "projects" / "jobs-market" / "data.json"


def collect():
    """Run every adapter, isolating failures. Returns (rows, failed_sources)."""
    rows, failed = [], []
    for name, fetch in REGISTRY:
        t0 = time.time()
        try:
            got = fetch()
            rows.extend(got)
            print(f"  [{name:14}] ok    {len(got):>5} jobs   ({time.time()-t0:.1f}s)")
        except Exception as e:
            failed.append(name)
            print(f"  [{name:14}] FAIL  {str(e)[:70]}")
    return rows, failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch only; print counts and a sample, write nothing")
    args = ap.parse_args()

    print("=" * 64)
    print("  Job-market ETL — fetching all sources")
    print("=" * 64)
    rows, failed = collect()

    print("-" * 64)
    print(f"  total collected: {len(rows)} jobs from "
          f"{len(REGISTRY) - len(failed)}/{len(REGISTRY)} sources")
    if failed:
        print(f"  sources that failed: {', '.join(failed)}")
    by_source = Counter(r["source"] for r in rows)
    print(f"  by source: {dict(by_source)}")
    by_market = Counter(r["market"] or "?" for r in rows)
    print(f"  by market: {dict(by_market)}")

    if rows:
        print("-" * 64)
        print("  sample row:")
        sample = dict(rows[0])
        sample["description"] = sample["description"][:120] + "…"
        for k, v in sample.items():
            print(f"    {k:16} {v}")

    if len(rows) == 0:
        print("  ERROR: zero jobs collected — failing the run.")
        sys.exit(1)

    if args.dry_run:
        print("=" * 64)
        print("  dry-run: nothing written.")
        return

    # ── classify ──
    for r in rows:
        classify.classify(r)
    by_area = Counter(r["area"] for r in rows)
    by_sen = Counter(r["seniority"] for r in rows)
    print(f"  by area: {dict(by_area.most_common())}")
    print(f"  by seniority: {dict(by_sen.most_common())}")

    # ── store (SQLite history) ──
    conn = storage.connect(str(DB_PATH))
    before = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    storage.upsert(conn, rows)
    total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    print(f"  stored: {total - before} new · {total} total in jobs.db")

    # ── export served snapshot (90-day window) ──
    n, mb = storage.export_snapshot(conn, str(JSON_PATH), window_days=90)
    conn.close()
    rel = os.path.relpath(JSON_PATH, HERE.parent)
    print(f"  snapshot: {n} jobs → {rel} ({mb:.2f} MB raw)")
    print("=" * 64)
    print("  done.")


if __name__ == "__main__":
    main()
