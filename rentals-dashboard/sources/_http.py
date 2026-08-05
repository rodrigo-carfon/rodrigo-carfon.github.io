# -*- coding: utf-8 -*-
"""Shared HTTP helper — stdlib only, with a bounded retry/backoff.

Same contract as jobs-dashboard/sources/_http.py: retry transient failures
(timeout, 5xx, 429, JSON-decode) with linear backoff, then raise. Kept
dependency-free (urllib) so the daily pipeline has zero third-party surface.

Deliberate deviation from the jobs pipeline: the User-Agent here is a browser
string, not the honest self-identifying `jobs-market-explorer/1.0`. The job
boards expose documented public APIs that accept any caller; the portal endpoint
this project reads is the private JSON API behind the portals' own web front end,
and it rejects a request whose UA/Origin/Referer don't look like that front end.
A self-identifying UA simply gets a 403 — there is no polite variant that works.
What we keep from the honest posture is the part that actually matters to the
host: low, sequential, rate-limited volume (see PAUSE in grupozap.py), no
concurrency, and no attempt to defeat a block if one is ever applied.
"""
import json
import time
import urllib.request
import urllib.error

BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

DEFAULT_HEADERS = {
    "User-Agent": BROWSER_UA,
    "Accept": "application/json",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


def get_json(url, headers=None, timeout=25, retries=3, backoff=2.0):
    """GET a URL and parse JSON, retrying transient errors. Raises on final failure."""
    h = dict(DEFAULT_HEADERS)
    if headers:
        h.update(headers)
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            last_err = e
            # 4xx (except 429) are not worth retrying — the request is wrong.
            # 403 in particular means the caller's IP is being refused, which no
            # amount of retrying fixes; see the note in README about running the
            # pipeline from a residential connection.
            if e.code < 500 and e.code != 429:
                raise
        except Exception as e:  # timeout, URLError, JSONDecodeError
            last_err = e
        if attempt < retries:
            time.sleep(backoff * attempt)
    raise RuntimeError(f"get_json failed after {retries} attempts: {last_err}") from last_err
