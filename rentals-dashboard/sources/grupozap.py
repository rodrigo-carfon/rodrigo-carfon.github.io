# -*- coding: utf-8 -*-
"""Grupo OLX network (VivaReal + ZAP Imóveis + OLX) — the "glue" JSON endpoint.

This is the single highest-yield source in Brazilian real estate: the three
largest portals in the country share one inventory, and each listing carries a
`portals` array saying which of them it appears on. Querying the VivaReal and ZAP
endpoints and taking the union covers OLX for free — an OLX-only adapter would
mostly re-fetch rows we already have.

Because the inventory is shared, a listing has the SAME numeric id on both
endpoints. Both adapters therefore emit `source="grupozap"` and the storage layer
keys on that id, so the union deduplicates itself instead of double-counting.

Why this endpoint at all, rather than parsing the portals' HTML: it is the JSON
the portals' own front end calls, so it returns clean typed fields — including
`displayAddressGeolocation`, which is what makes the 200 km radius filter exact
and removes any need for a geocoding service.

Two hard limits, both found by probing (see `python -m sources.grupozap --probe`):
  * `size` is capped at 24 — larger values 400.
  * a single query can only be paged so deep, so each shard must stay small.
Hence the shard grid below: portal × state × unit type × rent bucket, with a land
area floor. Without the floor, "HOME" alone is 68k listings in São Paulo; with it,
a few dozen.
"""
import sys
import time
import urllib.parse

from ._http import get_json
from ._common import listing, strip_html, as_int, first_int, iso_date

# ── endpoints ──────────────────────────────────────────────────────────────
PORTALS = {
    "vivareal": {"api": "https://glue-api.vivareal.com/v2/listings",
                 "site": "https://www.vivareal.com.br"},
    "zap":      {"api": "https://glue-api.zapimoveis.com.br/v2/listings",
                 "site": "https://www.zapimoveis.com.br"},
}

# ── shard grid ─────────────────────────────────────────────────────────────
# 200 km from Campinas reaches São Paulo state and the southern tip of Minas
# (Extrema, Camanducaia, Poços de Caldas). It does not reach RJ or PR, so
# querying them would only cost requests. Anything that slips through is dropped
# by the exact haversine filter later anyway.
STATES = ["São Paulo", "Minas Gerais"]

# FARM is the bulk of it. HOME is included because a large share of chácaras are
# filed as an ordinary house by whoever typed the ad — the land-area floor is what
# makes that tractable.
UNIT_TYPES = ["FARM", "COUNTRY_HOUSE", "ALLOTMENT_LAND", "HOME"]

# Rent buckets keep every shard well under the pagination ceiling. Measured on
# São Paulo/FARM, the fullest shard of all, no bucket exceeded ~625 listings.
#
# The R$30.000 ceiling is a scope decision, not a technical one. Inspecting the
# 227 listings above it: the median was R$50.000 and the contents were warehouses,
# commercial lots, a hotel and one ad asking R$1.111.111/month for a house —
# plainly a sale price typed into the rent field. None of it is somewhere to
# live, and letting it in would wreck the median-rent headline. R$30.000 is
# already 3x the rent this search is calibrated on.
PRICE_BUCKETS = [(0, 3000), (3000, 6000), (6000, 10000),
                 (10000, 15000), (15000, 30000)]

# Land-area floor, in m². Deliberately below the 4.000 m² match threshold in
# classify.py: an ad with a mistyped area still deserves to be seen and judged.
MIN_LAND_M2 = 3000

PAGE = 24            # API maximum; larger values return 400
MAX_PAGES = 42       # safety stop per shard (~1000 listings, the paging ceiling)
PAUSE = 0.4          # polite gap between requests, matching the jobs pipeline
MAX_PHOTOS = 8       # per listing, stored as media ids only

# Ask only for the fields we actually use. Roughly a third of the full payload,
# which is both faster and lighter on their servers.
INCLUDE_FIELDS = (
    "search(result(listings("
    "listing(id,title,description,unitTypes,usageTypes,usableAreas,totalAreas,"
    "bedrooms,bathrooms,suites,parkingSpaces,mergedAmenities,amenities,address,"
    "pricingInfos,createdAt,updatedAt,displayAddressGeolocation,portals,status),"
    "account(name),medias)),totalCount)"
)


def _headers(portal):
    """The endpoint rejects a request whose domain headers don't agree."""
    site = PORTALS[portal]["site"]
    return {"x-domain": site.replace("https://", ""), "Origin": site, "Referer": site + "/"}


def _url(portal, state, unit_type, price_min, price_max, offset):
    q = {
        "business": "RENTAL",
        "categoryPage": "RESULT",
        "addressState": state,
        "unitTypes": unit_type,
        "totalAreasMin": MIN_LAND_M2,
        "priceMin": price_min,
        "priceMax": price_max,
        "size": PAGE,
        "from": offset,
        "includeFields": INCLUDE_FIELDS,
    }
    return PORTALS[portal]["api"] + "?" + urllib.parse.urlencode(q)


def _rental_price(pricing_infos):
    """Pull the monthly-rent block out of pricingInfos.

    A listing can be advertised for sale AND for rent at once, and the endpoint
    returns both blocks even under `business=RENTAL` — reading the first entry
    blindly yields a R$290.000 sale price as if it were a monthly rent.

    Short-stay listings (period DAILY/WEEKLY) are also filtered out here: this
    project is looking for somewhere to live, not a weekend rental.
    """
    for p in pricing_infos or []:
        if p.get("businessType") != "RENTAL":
            continue
        period = ((p.get("rentalInfo") or {}).get("period") or "MONTHLY").upper()
        if period not in ("MONTHLY", ""):
            continue
        rent = as_int(p.get("price"))
        if not rent:
            continue
        iptu = as_int(p.get("iptu")) or as_int(p.get("yearlyIptu"))
        return rent, as_int(p.get("monthlyCondoFee")), iptu
    return None, None, None


def _photo_ids(medias):
    """medias[].url is a template; the 32-hex id is the only part worth storing.

    https://resizedimgs.vivareal.com/img/vr-listing/<id>/{description}.jpg
        ?action={action}&dimension={width}x{height}

    Keeping ids instead of full URLs cuts the served JSON by roughly 70%; the
    dashboard rebuilds the URL at the size it needs.
    """
    out = []
    for m in medias or []:
        if m.get("type") not in (None, "", "IMAGE"):
            continue
        mid = m.get("id") or ""
        if mid and mid.isalnum() and len(mid) <= 40:
            out.append(mid)
        if len(out) >= MAX_PHOTOS:
            break
    return out


def _parse(row, portal):
    """One API row → one normalized listing, or None if it isn't usable."""
    L = row.get("listing") or {}
    lid = L.get("id")
    if not lid or L.get("status") not in (None, "", "ACTIVE"):
        return None

    # Warehouses, commercial lots and industrial sheds are listed under the same
    # unit types as rural property and match the same land-area floor. The portal
    # tags them, so use the tag: keep anything flagged residential, and anything
    # untagged (rural ads are frequently left blank), drop the purely commercial.
    usage = [u for u in (L.get("usageTypes") or []) if u]
    if usage and "RESIDENTIAL" not in usage:
        return None

    rent, condo, iptu = _rental_price(L.get("pricingInfos"))
    if not rent:
        return None  # no monthly rent = nothing this dashboard can rank

    addr = L.get("address") or {}
    geo = L.get("displayAddressGeolocation") or {}
    portals = [p for p in (L.get("portals") or []) if p]

    # Link to a portal that actually carries the ad. /imovel/id-<id>/ 308s to the
    # canonical slug URL, so we never have to build (or keep in sync) the slug.
    site = PORTALS["vivareal" if "VIVAREAL" in portals else portal]["site"]

    return listing(
        "grupozap", lid,
        title=L.get("title", ""),
        url=f"{site}/imovel/id-{lid}/",
        description=strip_html(L.get("description", "")),
        city=(addr.get("city") or "").strip(),
        state=(addr.get("state") or "").strip(),
        lat=geo.get("lat"),
        lon=geo.get("lon"),
        rent=rent,
        condo_fee=condo,
        iptu=iptu,
        total_area=first_int(L.get("totalAreas")),
        usable_area=first_int(L.get("usableAreas")),
        bedrooms=first_int(L.get("bedrooms")),
        suites=first_int(L.get("suites")),
        bathrooms=first_int(L.get("bathrooms")),
        parking=first_int(L.get("parkingSpaces")),
        amenities_raw=L.get("mergedAmenities") or L.get("amenities") or [],
        photos=_photo_ids(row.get("medias")),
        advertiser=((row.get("account") or {}).get("name") or "").strip(),
        published_date=iso_date(L.get("createdAt")),
        unit_type_raw=(L.get("unitTypes") or [""])[0],
        portals=portals,
    )


def _fetch_shard(portal, state, unit_type, pmin, pmax, seen, out):
    """Page through one shard, appending new listings. Returns rows seen."""
    got = 0
    for pageno in range(MAX_PAGES):
        url = _url(portal, state, unit_type, pmin, pmax, pageno * PAGE)
        data = get_json(url, headers=_headers(portal))
        rows = (((data.get("search") or {}).get("result") or {}).get("listings")) or []
        for row in rows:
            lid = (row.get("listing") or {}).get("id")
            if not lid or lid in seen:
                continue
            seen.add(lid)
            rec = _parse(row, portal)
            if rec:
                out.append(rec)
        got += len(rows)
        if len(rows) < PAGE:
            break
        time.sleep(PAUSE)
    return got


def _fetch(portal):
    seen, out = set(), []
    for state in STATES:
        for unit_type in UNIT_TYPES:
            for pmin, pmax in PRICE_BUCKETS:
                _fetch_shard(portal, state, unit_type, pmin, pmax, seen, out)
                time.sleep(PAUSE)
    return out


def fetch():
    """Collect from VivaReal, falling back to ZAP if that endpoint is down.

    Measured, not assumed: over an identical shard grid both endpoints returned
    the same 580 listing ids — intersection 580, unique to either side 0. The
    inventory really is shared, so querying both doubles the runtime and doubles
    the load we put on their servers to collect nothing. ZAP therefore serves as
    a standby: same parser, same grid, used only when VivaReal fails outright.
    """
    try:
        return _fetch("vivareal")
    except Exception as e:
        print(f"    vivareal endpoint failed ({str(e)[:60]}) — retrying via zap")
        return _fetch("zap")


# ── probe ──────────────────────────────────────────────────────────────────
def _probe():
    """Print totalCount per shard without collecting, to sanity-check the grid.

    Run this first when the endpoint misbehaves: it separates "the API changed"
    from "our parsing changed", and shows immediately whether any shard is close
    to the paging ceiling and needs splitting further.
    """
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"{'portal':10} {'state':14} {'unit':16} {'rent bucket':>18}  total")
    print("-" * 68)
    for portal in PORTALS:
        grand = 0
        for state in STATES:
            for unit_type in UNIT_TYPES:
                for pmin, pmax in PRICE_BUCKETS:
                    url = _url(portal, state, unit_type, pmin, pmax, 0)
                    n = ((get_json(url, headers=_headers(portal)).get("search") or {})
                         .get("totalCount")) or 0
                    grand += n
                    if n:
                        bucket = f"{pmin//1000}k-{pmax//1000}k"
                        flag = "  ← near paging ceiling" if n > 900 else ""
                        print(f"{portal:10} {state:14} {unit_type:16} {bucket:>18}  {n:>5}{flag}")
                    time.sleep(PAUSE)
        print(f"{portal:10} {'TOTAL':14} {'':16} {'':>18}  {grand:>5}\n")


if __name__ == "__main__":
    _probe()
