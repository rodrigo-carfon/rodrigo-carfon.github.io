# -*- coding: utf-8 -*-
"""Durable storage (SQLite, full history) + the served snapshot (columnar JSON).

- rentals.db is the source of truth: every listing ever seen, with first/last-seen
  dates and a rent history.
- data.json is what the static dashboard fetch()es. It is dictionary-encoded
  (repeated strings → integer indices) and carries no description.

Three things this keeps that the portals themselves do not:

1. `first_seen_date`, stamped on INSERT and never updated — that is the whole
   basis of the "NEW" badge. The portals show a listing's creation date, which
   is not the same thing: an ad created months ago can appear in results for the
   first time today because its price just dropped into range.
2. `rent_history`, one row per actual change. A rental that is not moving gets
   its price cut, and that is the single strongest buy-signal in this market.
   Nobody exposes it, and it costs one integer per change to keep.
3. Personal data is kept OUT. The endpoint returns advertiser phones and a
   WhatsApp number; this repo is public and its .gitignore already says scraped
   lead data must never land in it. Phones are dropped in the adapter, free-text
   descriptions are scrubbed in _common.scrub_contacts, and the snapshot ships
   no description at all. The listing URL is the contact channel.
"""
import json
import os
import sqlite3
from datetime import date, timedelta

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    listing_uid      TEXT PRIMARY KEY,
    source           TEXT,
    portals          TEXT,
    title            TEXT,
    url              TEXT,
    property_type    TEXT,
    city             TEXT,
    state            TEXT,
    lat              REAL,
    lon              REAL,
    distance_km      REAL,
    distance_band    TEXT,
    geo_approx       INTEGER,
    rent             INTEGER,
    condo_fee        INTEGER,
    iptu             INTEGER,
    total_area       INTEGER,
    usable_area      INTEGER,
    price_per_m2     REAL,
    bedrooms         INTEGER,
    suites           INTEGER,
    bathrooms        INTEGER,
    parking          INTEGER,
    features         TEXT,
    photos           TEXT,
    advertiser       TEXT,
    is_match         INTEGER,
    published_date   TEXT,
    first_seen_date  TEXT,
    last_seen_date   TEXT,
    description      TEXT,
    dedupe_key       TEXT
);
CREATE INDEX IF NOT EXISTS idx_listings_dedupe ON listings(dedupe_key);
CREATE INDEX IF NOT EXISTS idx_listings_seen   ON listings(first_seen_date);
CREATE INDEX IF NOT EXISTS idx_listings_last   ON listings(last_seen_date);

CREATE TABLE IF NOT EXISTS rent_history (
    listing_uid  TEXT,
    date         TEXT,
    rent         INTEGER,
    PRIMARY KEY (listing_uid, date)
);

CREATE TABLE IF NOT EXISTS city_centroid (
    city  TEXT,
    state TEXT,
    lat   REAL,
    lon   REAL,
    PRIMARY KEY (city, state)
);
"""


def dedupe_key(row):
    """Fuzzy identity for "the same property, advertised twice".

    Cross-posting is the norm here: one chácara handed to four agencies becomes
    four ads with four titles and four ids. Coordinates rounded to 3 decimals
    (~110 m) plus coarse land and rent buckets identify the property well enough
    to COUNT the duplicates — which is all this is used for. Like the jobs
    pipeline, nothing is deleted; the card just says "on N ads", which is itself
    a useful signal about how hard the owner is pushing.

    Returns "" for listings placed at a city centroid — those all share one
    coordinate by construction and would collapse into a single fake cluster.
    """
    if row.get("geo_approx"):
        return ""
    lat, lon = row.get("lat"), row.get("lon")
    if lat is None or lon is None:
        return ""
    land = (row.get("total_area") or 0) // 1000
    rent = (row.get("rent") or 0) // 1000
    return f"{round(float(lat), 3)},{round(float(lon), 3)}|{land}|{rent}"


def connect(db_path):
    d = os.path.dirname(db_path)
    if d:
        os.makedirs(d, exist_ok=True)  # sqlite won't create the parent dir
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def load_centroids(conn):
    """Known city centroids, for listings that arrive without coordinates."""
    return {(c, s): (lat, lon)
            for c, s, lat, lon in conn.execute(
                "SELECT city, state, lat, lon FROM city_centroid")}


def save_centroids(conn, centroids):
    conn.executemany(
        "INSERT INTO city_centroid (city, state, lat, lon) VALUES (?,?,?,?) "
        "ON CONFLICT(city, state) DO UPDATE SET lat=excluded.lat, lon=excluded.lon",
        [(c, s, lat, lon) for (c, s), (lat, lon) in centroids.items()])
    conn.commit()


def upsert(conn, rows, today=None):
    """Insert new listings (stamping first_seen), refresh the rest, log rent moves.

    Returns (inserted, rent_changes).
    """
    today = today or date.today().isoformat()
    cur = conn.cursor()
    known = {uid: rent for uid, rent in
             conn.execute("SELECT listing_uid, rent FROM listings")}

    inserted = changes = 0
    for r in rows:
        uid = f"{r['source']}:{r['native_id']}"
        prev = known.get(uid, "missing")
        row = (
            uid, r["source"], " · ".join(r.get("portals") or []),
            r["title"], r["url"], r.get("property_type", ""),
            r["city"], r["state"], r.get("lat"), r.get("lon"),
            r.get("distance_km"), r.get("distance_band", ""), r.get("geo_approx", 0),
            r.get("rent"), r.get("condo_fee"), r.get("iptu"),
            r.get("total_area"), r.get("usable_area"), r.get("price_per_m2"),
            r.get("bedrooms"), r.get("suites"), r.get("bathrooms"), r.get("parking"),
            " · ".join(r.get("features") or []), ",".join(r.get("photos") or []),
            r.get("advertiser", ""), r.get("match", 0), r.get("published_date", ""),
            today, today, (r.get("description") or "")[:400], dedupe_key(r),
        )
        cur.execute("""
            INSERT INTO listings (listing_uid, source, portals, title, url,
                property_type, city, state, lat, lon, distance_km, distance_band,
                geo_approx, rent, condo_fee, iptu, total_area, usable_area,
                price_per_m2, bedrooms, suites, bathrooms, parking, features,
                photos, advertiser, is_match, published_date, first_seen_date,
                last_seen_date, description, dedupe_key)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(listing_uid) DO UPDATE SET
                last_seen_date = excluded.last_seen_date,
                portals = excluded.portals, title = excluded.title,
                url = excluded.url, property_type = excluded.property_type,
                city = excluded.city, state = excluded.state,
                lat = excluded.lat, lon = excluded.lon,
                distance_km = excluded.distance_km,
                distance_band = excluded.distance_band,
                geo_approx = excluded.geo_approx,
                rent = excluded.rent, condo_fee = excluded.condo_fee,
                iptu = excluded.iptu, total_area = excluded.total_area,
                usable_area = excluded.usable_area,
                price_per_m2 = excluded.price_per_m2,
                bedrooms = excluded.bedrooms, suites = excluded.suites,
                bathrooms = excluded.bathrooms, parking = excluded.parking,
                features = excluded.features, photos = excluded.photos,
                advertiser = excluded.advertiser, description = excluded.description,
                published_date = excluded.published_date,
                is_match = excluded.is_match, dedupe_key = excluded.dedupe_key
        """, row)
        # Every mutable column is refreshed above; `first_seen_date` is the one
        # deliberately absent from DO UPDATE SET, so it stays stamped at the
        # first sighting — that is what the "novo" badge reads. Anything left out
        # of that list silently freezes at whatever it was when the row was first
        # inserted, which is how the geo columns went stale during development.
        if prev == "missing":
            inserted += 1
        elif prev != r.get("rent"):
            changes += 1
        # One row per (listing, day) the price was observed at a new value.
        if prev == "missing" or prev != r.get("rent"):
            cur.execute("INSERT OR REPLACE INTO rent_history (listing_uid, date, rent) "
                        "VALUES (?,?,?)", (uid, today, r.get("rent")))
        known[uid] = r.get("rent")   # a repeated uid in `rows` is not a new row
    conn.commit()
    return inserted, changes


def prune(conn, keep_days=180, today=None):
    """Drop listings not seen in `keep_days`. The DB is committed daily, so a
    rolling window keeps git history bounded. Wider than the jobs pipeline's 120
    days: this market turns over slowly and the base is ~50x smaller."""
    today = today or date.today().isoformat()
    cutoff = (date.fromisoformat(today) - timedelta(days=keep_days)).isoformat()
    cur = conn.execute("DELETE FROM listings WHERE last_seen_date < ?", (cutoff,))
    conn.execute("DELETE FROM rent_history WHERE listing_uid NOT IN "
                 "(SELECT listing_uid FROM listings)")
    conn.commit()
    return cur.rowcount


def export_snapshot(conn, out_path, active_days=10, today=None, max_raw_mb=4,
                    match_rule=None):
    """Write the dictionary-encoded JSON the dashboard reads.

    Only listings still being advertised are served: `active_days` tolerates a
    few missed runs (a self-hosted runner on a desktop will miss some) without
    resurrecting ads that came down weeks ago.
    """
    today = today or date.today().isoformat()
    cutoff = (date.fromisoformat(today) - timedelta(days=active_days)).isoformat()
    rows = conn.execute("""
        SELECT listing_uid, portals, title, url, property_type, city, state,
               lat, lon, distance_km, distance_band, geo_approx, rent, condo_fee,
               total_area, usable_area, price_per_m2, bedrooms, suites, bathrooms,
               parking, features, photos, advertiser, is_match, published_date,
               first_seen_date, dedupe_key
        FROM listings
        WHERE last_seen_date >= ?
        ORDER BY first_seen_date DESC, rent ASC
    """, (cutoff,)).fetchall()

    # How many separate ads point at the same physical property.
    clusters = {}
    for r in rows:
        if r[27]:
            clusters[r[27]] = clusters.get(r[27], 0) + 1

    # Opening rent per listing, to show "was R$X, now R$Y".
    first_rent = {uid: rent for uid, rent in conn.execute("""
        SELECT listing_uid, rent FROM rent_history
        WHERE (listing_uid, date) IN (
            SELECT listing_uid, MIN(date) FROM rent_history GROUP BY listing_uid)
    """)}

    dicts = {c: [] for c in ("city", "state", "property_type", "advertiser",
                             "portals", "band", "feature")}
    idx = {c: {} for c in dicts}

    def code(col, val):
        val = val or ""
        d = idx[col]
        if val not in d:
            d[val] = len(dicts[col])
            dicts[col].append(val)
        return d[val]

    # `uid` is the one column the page cannot do without and can never reorder
    # around: the reader's own marks (kept / discarded / noted) are stored in her
    # browser against it. Row order changes every refresh as listings come and
    # go, so anything keyed on array position would scramble her picks overnight.
    cols = {k: [] for k in ("uid", "title", "url", "city", "st", "pt", "adv", "por",
                            "band", "km", "lat", "lon", "rent", "condo", "land",
                            "built", "ppm", "bed", "suite", "bath", "park",
                            "feat", "ph", "match", "pub", "seen", "nads",
                            "rent0", "approx")}
    for r in rows:
        (uid, portals, title, url, ptype, city, state, lat, lon, km, band, approx,
         rent, condo, land, built, ppm, bed, suite, bath, park, feats, photos,
         adv, match, pub, seen, dk) = r
        cols["uid"].append(uid)
        cols["title"].append(title or "")
        cols["url"].append(url or "")
        cols["city"].append(code("city", city))
        cols["st"].append(code("state", state))
        cols["pt"].append(code("property_type", ptype))
        cols["adv"].append(code("advertiser", adv))
        cols["por"].append(code("portals", portals))
        cols["band"].append(code("band", band))
        cols["km"].append(km)
        cols["lat"].append(round(lat, 5) if lat is not None else None)
        cols["lon"].append(round(lon, 5) if lon is not None else None)
        cols["rent"].append(rent)
        cols["condo"].append(condo)
        cols["land"].append(land)
        cols["built"].append(built)
        cols["ppm"].append(ppm)
        cols["bed"].append(bed)
        cols["suite"].append(suite)
        cols["bath"].append(bath)
        cols["park"].append(park)
        cols["feat"].append([code("feature", f) for f in (feats or "").split(" · ") if f])
        cols["ph"].append([p for p in (photos or "").split(",") if p])
        cols["match"].append(match or 0)
        cols["pub"].append((pub or "")[:10])
        cols["seen"].append((seen or "")[:10])
        cols["nads"].append(clusters.get(dk, 1) if dk else 1)
        # Only carry an opening rent when it actually differs — otherwise it is
        # one redundant integer per listing for no information.
        r0 = first_rent.get(uid)
        cols["rent0"].append(r0 if (r0 and rent and r0 != rent) else None)
        cols["approx"].append(approx or 0)

    total_base = conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
    # Ship the match thresholds rather than let the page restate them: the rule
    # lives in classify.py, and a hard-coded caption in the HTML would quietly
    # start lying the first time those constants move.
    payload = {"generated": today, "count": len(rows), "total_base": total_base,
               "radius_km": 200, "origin": "Campinas",
               "match_rule": match_rule or {},
               "dict": dicts, "listings": cols}
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    raw_mb = len(text.encode("utf-8")) / 1_048_576
    if raw_mb > max_raw_mb:
        raise RuntimeError(f"snapshot {raw_mb:.1f} MB exceeds {max_raw_mb} MB cap — "
                           f"trim photos per listing or tighten the active window")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    return len(rows), raw_mb
