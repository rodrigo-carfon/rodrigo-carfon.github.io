# Job-Market Explorer — daily multi-portal jobs pipeline

**A data project: eight public job-portal APIs → a normalized, classified base in
SQLite → an interactive dashboard.** Every posting is fetched daily, deduplicated,
tagged with an área and a seniority level, and kept for a 90-day window.

🔗 **[Live dashboard](https://rodrigo-carfon.github.io/projects/jobs-market/)** ·
refreshed daily by a scheduled workflow, no server.

## What it does

Turns nine unrelated public job APIs into one queryable, comparable dataset:

1. **Collect** — one adapter per portal fetches postings and maps them to a single
   normalized schema, so the pipeline never sees portal-specific fields.
2. **Classify** — derives área-de-atuação (data, engineering, product, marketing, …)
   and seniority (estágio → gestão) from structured hints when a portal provides
   them, else from the title.
3. **Store** — upserts into SQLite, stamping `first_seen`/`last_seen` and a
   cross-portal `seen_on_n_portals` signal, keeping the full history.
4. **Serve** — exports a trimmed, dictionary-encoded 90-day JSON snapshot that the
   static dashboard fetches and filters entirely client-side.

## Sources (all public, key-free)

| Portal | Market | Notes |
|---|---|---|
| **Gupy** | Brazil | the BR anchor — public `employability-portal` endpoint |
| **The Muse** | Global | structured seniority (`levels[]`) + category |
| **Remotive · Jobicy · RemoteOK · Himalayas · Working Nomads · Arbeitnow** | Global remote | six remote-job boards; RemoteOK also carries salary |

_Adzuna (free key, BR breadth + salary) has an adapter slot but is left out until a
key is provided — the registry drops it cleanly._

## Architecture

```
9 portal APIs                            ← public, key-free
     │  sources/*.py  (one adapter each → common schema)
     ▼
pipeline.py  ──►  fetch (isolated per source) → classify → store → export
     │
     ├─►  data/jobs.db                       (SQLite: full history, durable)
     └─►  ../projects/jobs-market/data.json  (90-day snapshot, columnar/dict-encoded)
                     │
                     ▼
        projects/jobs-market/index.html + app.js   (static dashboard, fetches the JSON)
```

- **Per-source isolation:** one flaky endpoint logs a failure and is skipped; the
  run only fails if *every* source fails or zero jobs are collected.
- **HTTP retry/backoff** lives in `sources/_http.py` (stdlib `urllib`, no deps).
- **The snapshot is dictionary-encoded** — repeated strings (source, company, area,
  seniority, …) become integer indices, and descriptions are dropped — so the file
  the browser downloads stays small even at tens of thousands of jobs.

## Automation

[`.github/workflows/refresh-jobs.yml`](../.github/workflows/refresh-jobs.yml) runs
daily (`cron: 20 6 * * *`, 06:20 UTC — job boards publish 7 days a week) plus a
manual *Run workflow* button. It runs the pipeline and commits `jobs.db` +
`data.json` only if something changed; GitHub Pages redeploys the dashboard.

## Repository layout

```
jobs-dashboard/
├── pipeline.py            # orchestrator: fetch → classify → store → export
├── classify.py            # área + seniority taxonomy (pure functions)
├── storage.py             # SQLite schema, upsert, 90-day columnar JSON export
├── sources/
│   ├── _http.py           # get_json() with retry/backoff (stdlib only)
│   ├── _common.py         # normalized-job builder + shared helpers
│   ├── gupy.py            # Brazil
│   ├── themuse.py         # structured seniority/category
│   └── remote_boards.py   # the six remote boards
├── requirements.txt       # (empty — standard library only)
└── data/jobs.db           # generated: full history (do not hand-edit)

projects/jobs-market/
├── index.html + app.js    # the static dashboard
└── data.json              # generated: the served 90-day snapshot
```

## How to run

```bash
cd jobs-dashboard
python pipeline.py                 # fetch all sources → jobs.db + data.json
#   (add --dry-run to fetch and print counts without writing anything)

# preview the dashboard over HTTP from the repo root:
cd .. && python -m http.server 8000
# → http://localhost:8000/projects/jobs-market/
```

## Disclaimer

Data comes from third-party public job-portal APIs and reflects whatever they
expose; endpoints are undocumented and may change. This is a portfolio / educational
project.
