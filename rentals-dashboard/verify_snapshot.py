# -*- coding: utf-8 -*-
"""Contract check between storage.export_snapshot() and the dashboard page.

The page is vanilla JS with no build step and no test runner, so the failure
mode it is actually exposed to is a silent contract drift: someone renames a
column in storage.py, `L.rent` becomes undefined in the browser, and the page
renders a grid of "R$ –" with no error anywhere. This script asserts, against
the real generated file, every key and index the page dereferences — plus the
label strings the two sides hard-code independently.

Run it after any change to export_snapshot() or to the page's data access:

    python verify_snapshot.py
"""
import io
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).parent
SNAP = HERE.parent / "projects" / "countryside-rentals" / "data.json"
PAGE = HERE.parent / "projects" / "countryside-rentals" / "index.html"

# Every L.<key> and D.<key> the page reads. Kept explicit rather than scraped
# from the HTML, so a typo on either side is caught instead of mirrored.
COLUMNS = ["uid", "title", "url", "city", "st", "pt", "adv", "por", "band", "km", "lat",
           "lon", "rent", "condo", "land", "built", "ppm", "bed", "suite", "bath",
           "park", "feat", "ph", "match", "pub", "seen", "nads", "rent0", "approx"]
DICTS = ["city", "state", "property_type", "advertiser", "portals", "band", "feature"]
DICT_COLUMNS = {"city": "city", "st": "state", "pt": "property_type",
                "adv": "advertiser", "por": "portals", "band": "band"}

CURRENT_RENT, CURRENT_LAND = 10000, 6000     # mirrors CURRENT in the page
X0, X1, Y1 = 3000, 100000, 30000             # mirrors the scatter domain

fails, warns = [], []


def check(cond, msg):
    (print(f"  [ok  ] {msg}") if cond else fails.append(msg))
    if not cond:
        print(f"  [FAIL] {msg}")


def main():
    if not SNAP.exists():
        print(f"missing {SNAP} — run pipeline.py first")
        sys.exit(1)
    raw = io.open(SNAP, encoding="utf-8").read()
    d = json.loads(raw)
    L, D, N = d["listings"], d["dict"], d["count"]

    print(f"snapshot: {N} listings · {len(raw.encode('utf-8'))/1048576:.2f} MB\n")

    print("── payload keys ──")
    for k in ("generated", "count", "total_base", "radius_km", "origin"):
        check(k in d, f"top-level key '{k}'")
    for c in COLUMNS:
        check(c in L, f"listings.{c}")
    for c in DICTS:
        check(c in D, f"dict.{c}")

    print("\n── column lengths ──")
    bad = [c for c in COLUMNS if c in L and len(L[c]) != N]
    check(not bad, f"all {len(COLUMNS)} columns have length {N}" +
          (f" — wrong: {bad}" if bad else ""))

    print("\n── dictionary indices in range ──")
    for col, dk in DICT_COLUMNS.items():
        if col not in L or dk not in D:
            continue
        hi = len(D[dk])
        bad = [v for v in L[col] if not isinstance(v, int) or not (0 <= v < hi)]
        check(not bad, f"{col} → dict.{dk} ({hi} entries), {len(bad)} out of range")
    hi = len(D["feature"])
    bad = [v for row in L["feat"] for v in row if not (0 <= v < hi)]
    check(not bad, f"feat → dict.feature ({hi} entries), {len(bad)} out of range")

    print("\n── the page's hard-coded labels exist in the data ──")
    page = io.open(PAGE, encoding="utf-8").read()
    m = re.search(r"var BAND_ORDER = \[(.*?)\];", page, re.S)
    check(bool(m), "page declares BAND_ORDER")
    if m:
        order = re.findall(r'"([^"]+)"', m.group(1))
        missing = [b for b in D["band"] if b and b not in order]
        check(not missing, f"every dict.band label is in BAND_ORDER — missing: {missing}")

    print("\n── no personal data ──")
    # The listing id is a 10-digit number inside the URL and trips any phone
    # regex, so check every field except url.
    phone = re.compile(r"(?<!\d)(?:\(?\d{2}\)?[\s.-]*)?9?[\s.-]?\d{4}[\s.-]?\d{4}(?!\d)")
    leaks = []
    for pool in (L["title"], D["city"], D["advertiser"], D["property_type"]):
        leaks += [v for v in pool if isinstance(v, str) and phone.search(v)]
    check(not leaks, f"no phone-shaped strings outside url — found {len(leaks)}")
    check("description" not in L, "no description column is shipped")
    check("whatsapp" not in raw.lower(), "the string 'whatsapp' does not appear")
    urls_ok = all(re.fullmatch(r"https://www\.(vivareal|zapimoveis)\.com\.br/imovel/id-\d+/", u)
                  for u in L["url"])
    check(urls_ok, "every url is a bare /imovel/id-<n>/ link")

    print("\n── geo ──")
    kms = [k for k in L["km"] if k is not None]
    check(len(kms) == N, f"every listing has a distance ({len(kms)}/{N})")
    check(max(kms) <= d["radius_km"], f"max distance {max(kms)} km <= {d['radius_km']}")

    print("\n── what the page will actually render ──")
    plotted = [i for i in range(N) if L["rent"][i] and L["land"][i]
               and X0 <= L["land"][i] <= X1 and L["rent"][i] <= Y1]
    off = sum(1 for i in range(N) if L["rent"][i] and L["land"][i]) - len(plotted)
    cheaper = sum(1 for i in plotted
                  if L["rent"][i] < CURRENT_RENT and L["land"][i] >= CURRENT_LAND)
    print(f"  scatter: {len(plotted)} points on-axis, {off} outside")
    print(f"  cheaper than the current rental with >= as much land: {cheaper}")
    if len(plotted) < N * 0.6:
        warns.append(f"only {len(plotted)}/{N} listings land inside the scatter domain")
    print(f"  cards with at least one photo: {sum(1 for p in L['ph'] if p)}/{N}")
    print(f"  target-profile matches: {sum(L['match'])}")
    print(f"  listings with a recorded price drop: "
          f"{sum(1 for i in range(N) if L['rent0'][i] and L['rent'][i] and L['rent0'][i] > L['rent'][i])}")

    # Every filter chip must select something — an always-empty chip is a bug.
    print("\n── filter buckets ──")
    for name, col, buckets in [
        ("rent", L["rent"], [(0, 4000), (4000, 6000), (6000, 10000), (10000, 14000), (14000, 1e18)]),
        ("land", L["land"], [(3000, 5000), (5000, 10000), (10000, 20000), (20000, 100000), (100000, 1e18)]),
    ]:
        counts = [sum(1 for v in col if v is not None and lo <= v < hi) for lo, hi in buckets]
        check(all(c > 0 for c in counts), f"{name} buckets all non-empty: {counts}")
    beds = [sum(1 for v in L["bed"] if v is not None and lo <= v <= hi)
            for lo, hi in [(1, 2), (3, 3), (4, 4), (5, 10**9)]]
    check(all(c > 0 for c in beds), f"bedroom buckets all non-empty: {beds}")

    print()
    if warns:
        for w in warns:
            print(f"  [warn] {w}")
    if fails:
        print(f"\nFAILED — {len(fails)} check(s):")
        for f in fails:
            print(f"  · {f}")
        sys.exit(1)
    print("all contract checks pass.")


if __name__ == "__main__":
    main()
