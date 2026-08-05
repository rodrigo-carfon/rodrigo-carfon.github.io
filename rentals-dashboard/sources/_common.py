# -*- coding: utf-8 -*-
"""Shared normalization helpers used by every source adapter.

Every adapter returns a list of dicts in ONE common shape (see `listing()`), so
the pipeline never sees portal-specific fields. Geo resolution (distance from
Campinas) and classification (property type, features, match) are later steps —
adapters may pass through structured hints in `amenities_raw`.

Money is stored in whole BRL (int); areas in whole m² (int). Both arrive from the
portals as strings, sometimes empty, sometimes with junk — `as_int` is the single
place that decides what a bad value means (None, never 0: a missing rent and a
free rent are different facts, and the dashboard sorts on rent).
"""
import re
import html as ihtml
from datetime import datetime, timezone


# Advertisers routinely paste a phone number, a WhatsApp or an e-mail into the
# free-text description ("Fone 9...", "zap 11 9...", "(19) 3232-1010"). Dropping
# the dedicated contact fields is therefore not enough — the same personal data
# leaks in through the description. Scrub it at the normalization boundary so no
# adapter can forget to, and so it never reaches the committed DB.
_PHONE_RE = re.compile(
    r"(?:\(?\d{2}\)?[\s.-]*)?(?:9[\s.-]*)?\d{4}[\s.-]?\d{4}"   # BR landline/mobile
    r"|\+?55[\s.-]?\d{2}[\s.-]?\d{4,5}[\s.-]?\d{4}"            # +55 international
)
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b")
_URL_RE = re.compile(r"\b(?:https?://|www\.)\S+", re.I)


def scrub_contacts(s):
    """Remove phone numbers, e-mails and outbound links from free text."""
    s = _EMAIL_RE.sub("[email]", s or "")
    s = _URL_RE.sub("[link]", s)
    return _PHONE_RE.sub("[phone]", s)


def strip_html(s, limit=4000):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = ihtml.unescape(s)
    s = scrub_contacts(s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s[:limit]


def as_int(value):
    """Portal numerics arrive as strings ('2354', '', '0', None, '1.600').
    Return a positive int, or None when the value carries no information."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        n = int(value)
        return n if n > 0 else None
    s = str(value).strip()
    if not s:
        return None
    s = re.sub(r"[^\d]", "", s.split(",")[0])   # drop separators / currency marks
    if not s:
        return None
    try:
        n = int(s)
    except ValueError:
        return None
    return n if n > 0 else None


def first_int(seq):
    """Portals return these as single-element lists: ['2354'] → 2354, [] → None."""
    if not seq:
        return None
    return as_int(seq[0] if isinstance(seq, (list, tuple)) else seq)


def iso_date(value):
    """Best-effort normalization of a portal's date field to 'YYYY-MM-DD'.
    Accepts ISO strings, epoch seconds (int/str), or None."""
    if value is None or value == "":
        return ""
    try:
        n = int(value)
        if n > 10_000_000:  # plausibly a unix timestamp, not a year
            return datetime.fromtimestamp(n, tz=timezone.utc).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass
    s = str(value).strip()
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s)
    return m.group(1) if m else ""


def listing(source, native_id, title, url, **extra):
    """Build one normalized listing dict. `extra` may set any optional field.

    Note what is NOT here: advertiser phone and WhatsApp. The portal payload
    carries both, this repo is public, and the .gitignore already states that
    scraped lead data must never land in it. The listing URL is the contact
    channel; personal numbers are dropped at the adapter boundary so they cannot
    reach the DB or the served JSON by accident later.
    """
    d = {
        "source": source,
        "native_id": str(native_id) if native_id is not None else "",
        "title": (title or "").strip(),
        "url": url or "",
        "description": "",
        "property_type": "",       # set by classify
        "city": "",
        "state": "",
        "lat": None,
        "lon": None,
        "distance_km": None,       # set by geo
        "rent": None,              # BRL/month
        "condo_fee": None,
        "iptu": None,
        "total_area": None,        # land, m²
        "usable_area": None,       # built, m²
        "bedrooms": None,
        "suites": None,
        "bathrooms": None,
        "parking": None,
        "amenities_raw": [],       # portal's own enum strings — hints for classify
        "features": [],            # set by classify (normalized English labels)
        "photos": [],              # media ids; the page rebuilds the CDN URL
        "advertiser": "",          # agency name only — attribution, not a contact
        "published_date": "",
    }
    d.update(extra)
    return d
