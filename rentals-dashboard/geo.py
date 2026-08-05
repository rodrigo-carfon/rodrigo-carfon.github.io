# -*- coding: utf-8 -*-
"""Distance from Campinas — the filter the whole project is organized around.

The search is "within 200 km of Campinas", and the portal payload already
carries each listing's own coordinates, so this is exact arithmetic rather than
an approximation over city names. That is why there is no geocoding service
here, no municipality table, and no API key: a listing's own lat/lon beats a
city centroid, because a chácara sits in the rural belt of its município, not
in the town square.

The centroid machinery below exists only as a fallback for the occasional ad
published with no coordinates. It is self-hosted in the sense that matters:
the centroid of a city is the median of the listings in that city that DO have
coordinates. No external lookup, no rate limit, and it improves on its own as
the base grows. Median rather than mean, so one ad geocoded into the ocean
cannot drag a whole city with it.
"""
import math
from statistics import median

# Campinas city centre. Everything in this project is measured from here.
CAMPINAS = (-22.9099, -47.0626)
RADIUS_KM = 200

EARTH_R = 6371.0

# Chips on the dashboard. Upper bound is exclusive except for the last band.
# Labels are written in Portuguese here, at the source, so the page renders the
# stored value verbatim and the browser never translates anything. Keep these in
# lockstep with BAND_ORDER in projects/countryside-rentals/index.html — the page
# sorts the distance chips by that list, and verify_snapshot.py asserts the two
# still agree.
BANDS = [(25, "até 25 km"), (50, "25–50 km"), (100, "50–100 km"),
         (150, "100–150 km"), (RADIUS_KM, "150–200 km")]


def haversine(lat1, lon1, lat2, lon2):
    """Great-circle distance in km."""
    p = math.radians
    dlat = p(lat2 - lat1)
    dlon = p(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(p(lat1)) * math.cos(p(lat2)) * math.sin(dlon / 2) ** 2)
    return 2 * EARTH_R * math.asin(math.sqrt(a))


def distance_km(lat, lon):
    """Distance from Campinas, or None when the point is unusable."""
    if lat is None or lon is None:
        return None
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return None
    # (0, 0) is the classic "geocoder gave up" value, and it is in the Atlantic.
    if lat == 0 and lon == 0:
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return haversine(CAMPINAS[0], CAMPINAS[1], lat, lon)


def band(km):
    if km is None:
        return ""
    for upper, label in BANDS:
        if km <= upper:
            return label
    return ""


def _key(row):
    return ((row.get("city") or "").strip().lower(),
            (row.get("state") or "").strip().lower())


def centroids_from(rows):
    """Median coordinate per (city, state), over the rows that have one."""
    buckets = {}
    for r in rows:
        if r.get("lat") is None or r.get("lon") is None:
            continue
        if distance_km(r["lat"], r["lon"]) is None:
            continue
        buckets.setdefault(_key(r), []).append((float(r["lat"]), float(r["lon"])))
    return {k: (median(p[0] for p in v), median(p[1] for p in v))
            for k, v in buckets.items() if k[0]}


def resolve(rows, known=None):
    """Attach distance_km / distance_band to every row; drop what falls outside.

    Returns (kept_rows, stats). Rows are never discarded silently — every drop
    lands in a counter the pipeline prints, so a source quietly starting to omit
    coordinates shows up as a number instead of as missing listings.
    """
    centroids = dict(known or {})
    centroids.update(centroids_from(rows))   # this run's data wins, it's fresher

    kept = []
    stats = {"no_geo_resolved": 0, "dropped_no_geo": 0, "dropped_far": 0}
    for r in rows:
        km = distance_km(r.get("lat"), r.get("lon"))
        if km is None:
            c = centroids.get(_key(r))
            if c:
                r["lat"], r["lon"] = c
                km = distance_km(c[0], c[1])
                r["geo_approx"] = 1        # the card shows "approximate location"
                stats["no_geo_resolved"] += 1
        if km is None:
            stats["dropped_no_geo"] += 1
            continue
        if km > RADIUS_KM:
            stats["dropped_far"] += 1
            continue
        r["distance_km"] = round(km, 1)
        r["distance_band"] = band(km)
        kept.append(r)
    return kept, stats
