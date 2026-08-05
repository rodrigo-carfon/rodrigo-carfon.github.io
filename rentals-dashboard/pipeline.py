# -*- coding: utf-8 -*-
"""Countryside-rentals ETL — orchestrator.

Fetches every source in the registry with per-source isolation (one flaky portal
never aborts the run), merges the duplicate rows the shared-inventory endpoints
inevitably return, resolves each listing's distance from Campinas, classifies it,
stores it to SQLite and exports the served JSON snapshot.

Usage:
  python pipeline.py --dry-run     # fetch + geo + classify, print stats, write nothing
  python pipeline.py               # full run
"""
import sys
import os
import time
import argparse
from collections import Counter
from pathlib import Path

from sources import REGISTRY
import classify
import geo
import storage

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).parent
DB_PATH = HERE / "data" / "rentals.db"
JSON_PATH = HERE.parent / "projects" / "countryside-rentals" / "data.json"


def collect():
    """Run every adapter, isolating failures. Returns (rows, failed_sources)."""
    rows, failed = [], []
    for name, fetch in REGISTRY:
        t0 = time.time()
        try:
            got = fetch()
            rows.extend(got)
            print(f"  [{name:12}] ok    {len(got):>5} listings   ({time.time()-t0:.1f}s)")
        except Exception as e:
            failed.append(name)
            print(f"  [{name:12}] FAIL  {str(e)[:70]}")
    return rows, failed


def merge_duplicates(rows):
    """Collapse rows that are literally the same listing seen twice.

    VivaReal and ZAP serve one shared inventory, so a listing published on both
    comes back from both adapters under the SAME id. Keeping both would double
    every count on the dashboard. The keeper is the row with the most photos —
    the endpoints occasionally truncate the media array — and the `portals` lists
    are unioned so the card still says where the ad runs.
    """
    best = {}
    for r in rows:
        uid = (r["source"], r["native_id"])
        cur = best.get(uid)
        if cur is None:
            best[uid] = r
            continue
        cur["portals"] = sorted(set(cur.get("portals") or []) | set(r.get("portals") or []))
        if len(r.get("photos") or []) > len(cur.get("photos") or []):
            r["portals"] = cur["portals"]
            best[uid] = r
    return list(best.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch, geo-resolve and classify; print stats, write nothing")
    args = ap.parse_args()

    print("=" * 68)
    print("  Countryside rentals ETL — fetching all sources")
    print("=" * 68)
    raw, failed = collect()

    rows = merge_duplicates(raw)
    print("-" * 68)
    print(f"  collected: {len(raw)} rows → {len(rows)} unique listings from "
          f"{len(REGISTRY) - len(failed)}/{len(REGISTRY)} sources")
    if failed:
        print(f"  sources that failed: {', '.join(failed)}")

    if not rows:
        print("  ERROR: zero listings collected — failing the run.")
        sys.exit(1)

    # ── geo: distance from Campinas, then the 200 km cut ──
    known = {}
    if DB_PATH.exists():
        c = storage.connect(str(DB_PATH))
        known = storage.load_centroids(c)
        c.close()
    before = len(rows)
    rows, gstats = geo.resolve(rows, known)
    print(f"  geo: {len(rows)} within {geo.RADIUS_KM} km of Campinas "
          f"(of {before}) · {gstats['dropped_far']} too far · "
          f"{gstats['dropped_no_geo']} without usable coordinates · "
          f"{gstats['no_geo_resolved']} placed at a city centroid")

    if not rows:
        print("  ERROR: nothing left after the radius filter — failing the run.")
        sys.exit(1)

    # ── classify ──
    for r in rows:
        classify.classify(r)

    by_type = Counter(r["property_type"] for r in rows)
    by_band = Counter(r["distance_band"] for r in rows)
    matches = sum(r["match"] for r in rows)
    print(f"  by type: {dict(by_type.most_common())}")
    print(f"  by distance: {dict(sorted(by_band.items(), key=lambda kv: kv[0]))}")
    print(f"  ideal matches (R${classify.MATCH_RENT_MIN:,}–{classify.MATCH_RENT_MAX:,} "
          f"and ≥{classify.MATCH_LAND_MIN:,} m²): {matches}")

    rents = sorted(r["rent"] for r in rows if r["rent"])
    if rents:
        print(f"  rent: median R${rents[len(rents)//2]:,} · "
              f"range R${rents[0]:,}–R${rents[-1]:,}")

    if args.dry_run:
        print("-" * 68)
        print("  sample listing:")
        s = dict(sorted(rows[0].items()))
        s["description"] = (s.get("description") or "")[:100] + "…"
        for k, v in s.items():
            print(f"    {k:16} {v}")
        print("=" * 68)
        print("  dry-run: nothing written.")
        return

    # ── store (SQLite history) ──
    conn = storage.connect(str(DB_PATH))
    storage.save_centroids(conn, geo.centroids_from(rows))
    inserted, changes = storage.upsert(conn, rows)
    pruned = storage.prune(conn, keep_days=180)
    total = conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
    print(f"  stored: {inserted} new · {changes} rent changes · "
          f"{pruned} pruned (>180d) · {total} total in rentals.db")

    # ── export served snapshot ──
    n, mb = storage.export_snapshot(conn, str(JSON_PATH))
    conn.close()
    rel = os.path.relpath(JSON_PATH, HERE.parent)
    print(f"  snapshot: {n} listings → {rel} ({mb:.2f} MB raw)")
    print("=" * 68)
    print("  done.")


if __name__ == "__main__":
    main()
