# -*- coding: utf-8 -*-
"""Durable storage (SQLite, full history) + the served snapshot (columnar JSON).

- jobs.db is the source of truth: every job ever seen, with first/last-seen dates.
- data.json is a trimmed 90-day window the static dashboard fetch()es. It is
  dictionary-encoded (repeated strings → integer indices) and carries no
  description, so it stays small over the wire.
"""
import json
import re
import sqlite3
import unicodedata
from datetime import date, timedelta

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_uid          TEXT PRIMARY KEY,
    source           TEXT,
    title            TEXT,
    company          TEXT,
    area             TEXT,
    seniority        TEXT,
    work_model       TEXT,
    city             TEXT,
    state            TEXT,
    country          TEXT,
    market           TEXT,
    salary_min       REAL,
    salary_max       REAL,
    salary_currency  TEXT,
    published_date   TEXT,
    first_seen_date  TEXT,
    last_seen_date   TEXT,
    url              TEXT,
    skills           TEXT,
    description      TEXT,
    dedupe_key       TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_dedupe ON jobs(dedupe_key);
CREATE INDEX IF NOT EXISTS idx_jobs_seen   ON jobs(first_seen_date);
"""

_STOP = re.compile(r"\b(pleno|s[eê]nior|j[uú]nior|jr|sr|senior|junior|especialista|"
                   r"analista|estagi\w*|trainee|remoto|remote|home\s*office|\d+)\b", re.I)


def dedupe_key(title, company):
    def norm(s):
        s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
        s = _STOP.sub(" ", s)
        return re.sub(r"[^a-z0-9]+", " ", s).strip()
    return f"{norm(title)}|{norm(company)}"


def connect(db_path):
    import os
    d = os.path.dirname(db_path)
    if d:
        os.makedirs(d, exist_ok=True)  # sqlite won't create the parent dir
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def upsert(conn, jobs, today=None):
    """Insert new jobs (stamping first_seen), refresh mutable fields on the rest."""
    today = today or date.today().isoformat()
    cur = conn.cursor()
    inserted = 0
    for j in jobs:
        uid = f"{j['source']}:{j['native_id'] or j['url']}"
        dk = dedupe_key(j["title"], j["company"])
        skills = " · ".join((j.get("skills") or [])[:6])
        # Store only a short snippet: the dashboard never reads the description
        # (data.json excludes it), and keeping full text would bloat the committed
        # DB by ~5x. 400 chars is enough for any future keyword/snippet use.
        snippet = (j["description"] or "")[:400]
        row = (uid, j["source"], j["title"], j["company"], j.get("area", ""),
               j.get("seniority", ""), j["work_model"], j["city"], j["state"],
               j["country"], j["market"], j["salary_min"], j["salary_max"],
               j["salary_currency"], j["published_date"], today, today, j["url"],
               skills, snippet, dk)
        cur.execute("""
            INSERT INTO jobs (job_uid, source, title, company, area, seniority,
                work_model, city, state, country, market, salary_min, salary_max,
                salary_currency, published_date, first_seen_date, last_seen_date,
                url, skills, description, dedupe_key)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(job_uid) DO UPDATE SET
                last_seen_date = excluded.last_seen_date,
                title = excluded.title, company = excluded.company,
                area = excluded.area, seniority = excluded.seniority,
                work_model = excluded.work_model, salary_min = excluded.salary_min,
                salary_max = excluded.salary_max, url = excluded.url
        """, row)
        inserted += 1 if cur.rowcount == 1 else 0
    conn.commit()
    return inserted


def export_snapshot(conn, out_path, window_days=90, today=None, max_jobs=15000, max_raw_mb=9):
    """Write the dictionary-encoded JSON the dashboard reads.

    The durable base (jobs.db) keeps every job; the served snapshot is bounded to
    the `max_jobs` freshest jobs inside the `window_days` window, so the file the
    browser downloads and filters stays small and fast even as the base grows.
    """
    today = today or date.today().isoformat()
    cutoff = (date.fromisoformat(today) - timedelta(days=window_days)).isoformat()
    rows = conn.execute("""
        SELECT source, title, company, area, seniority, work_model, city, state,
               country, market, salary_min, salary_max, published_date,
               first_seen_date, url, skills, dedupe_key
        FROM jobs
        WHERE MAX(COALESCE(published_date,''), first_seen_date) >= ?
        ORDER BY MAX(COALESCE(published_date,''), first_seen_date) DESC
        LIMIT ?
    """, (cutoff, max_jobs)).fetchall()

    # seen_on_n_portals: distinct sources per dedupe_key across the window
    portals = {}
    for r in rows:
        portals.setdefault(r[16], set()).add(r[0])
    n_portals = {k: len(v) for k, v in portals.items()}

    dicts = {c: [] for c in ("source", "company", "area", "seniority",
                             "work_model", "market", "country")}
    idx = {c: {} for c in dicts}

    def code(col, val):
        val = val or ""
        d = idx[col]
        if val not in d:
            d[val] = len(dicts[col])
            dicts[col].append(val)
        return d[val]

    cols = {k: [] for k in ("title", "src", "cmp", "area", "sen", "wm", "mk",
                            "co", "city", "pub", "seen", "url", "np", "sk",
                            "smin", "smax")}
    for r in rows:
        (source, title, company, area, seniority, wm, city, state, country,
         market, smin, smax, pub, seen, url, skills, dk) = r
        cols["title"].append(title or "")
        cols["src"].append(code("source", source))
        cols["cmp"].append(code("company", company))
        cols["area"].append(code("area", area))
        cols["sen"].append(code("seniority", seniority))
        cols["wm"].append(code("work_model", wm))
        cols["mk"].append(code("market", market))
        cols["co"].append(code("country", country))
        cols["city"].append(city or state or "")
        cols["pub"].append((pub or seen or "")[:10])
        cols["seen"].append((seen or "")[:10])
        cols["url"].append(url or "")
        cols["np"].append(n_portals.get(dk, 1))
        cols["sk"].append(skills or "")
        cols["smin"].append(round(smin) if smin else None)
        cols["smax"].append(round(smax) if smax else None)

    total_window = conn.execute("""
        SELECT COUNT(*) FROM jobs
        WHERE MAX(COALESCE(published_date,''), first_seen_date) >= ?
    """, (cutoff,)).fetchone()[0]
    total_base = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

    payload = {"generated": today, "window_days": window_days,
               "count": len(rows), "total_window": total_window,
               "total_base": total_base, "dict": dicts, "jobs": cols}
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    raw_mb = len(text.encode("utf-8")) / 1_048_576
    if raw_mb > max_raw_mb:
        raise RuntimeError(f"snapshot {raw_mb:.1f} MB exceeds {max_raw_mb} MB cap — "
                           f"tighten the window or trim fields")

    import os
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    return len(rows), raw_mb
