# -*- coding: utf-8 -*-
"""Shared normalization helpers used by every source adapter.

Every adapter returns a list of dicts in ONE common shape (see `job()`), so the
pipeline never sees portal-specific fields. Classification (area/seniority) is a
later step — adapters may pass through structured hints in `levels`/`categories`.
"""
import re
import html as ihtml
from datetime import datetime, timezone


def strip_html(s, limit=6000):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = ihtml.unescape(s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s[:limit]


def iso_date(value):
    """Best-effort normalization of a portal's date field to 'YYYY-MM-DD'.
    Accepts ISO strings, epoch seconds (int/str), or None."""
    if value is None or value == "":
        return ""
    # epoch seconds?
    try:
        n = int(value)
        if n > 10_000_000:  # plausibly a unix timestamp, not a year
            return datetime.fromtimestamp(n, tz=timezone.utc).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass
    s = str(value).strip()
    # take the leading YYYY-MM-DD if present
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s)
    return m.group(1) if m else ""


def work_model_pt(remote_flag=None, raw=None):
    """Normalize a work-model to remoto / híbrido / presencial / '' (unknown)."""
    if remote_flag is True:
        return "remoto"
    t = (raw or "").lower()
    if any(k in t for k in ("remote", "remoto", "anywhere", "home office", "home-office")):
        return "remoto"
    if any(k in t for k in ("hybrid", "híbrido", "hibrido")):
        return "híbrido"
    if any(k in t for k in ("on-site", "onsite", "presencial", "in office", "in-office")):
        return "presencial"
    return ""


def job(source, native_id, title, company, url, **extra):
    """Build one normalized job dict. `extra` may set any of the optional fields."""
    d = {
        "source": source,
        "native_id": str(native_id) if native_id is not None else "",
        "title": (title or "").strip(),
        "company": (company or "").strip(),
        "url": url or "",
        "work_model": "",
        "city": "",
        "state": "",
        "country": "",
        "market": "",          # "BR" | "Global remote"
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "published_date": "",
        "skills": [],
        "description": "",
        "levels": [],          # structured seniority hints (The Muse)
        "categories": [],      # structured area hints (The Muse / Adzuna)
    }
    d.update(extra)
    return d
