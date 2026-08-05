# -*- coding: utf-8 -*-
"""Property type, features and the "ideal match" rule.

Follows the same i18n mechanism as jobs-dashboard/classify.py — labels are
resolved once here and stored, so the browser does zero translation — but lands
on the opposite language. The jobs dashboard is a portfolio piece written for an
English-reading audience; this one is a working tool for someone house-hunting in
São Paulo state. Labels are therefore Portuguese, which is also the language of
the ads being matched, so pattern and label finally agree.

Resolution order mirrors the jobs classifier: the portal's own structured hint
first (unitTypes, the amenities enum), keyword matching on title/description
second. Rural ads are written loosely and the structured fields are often left
at their defaults, so the keyword pass carries more weight here than it does for
job postings.
"""
import re
import unicodedata

# ── the search this project exists to answer ───────────────────────────────
# Calibrated on the current rental being replaced: 6.000 m² at R$10.000/month.
# The band is deliberately wide on both sides — an ad R$500 over the ceiling is
# still worth a look, and this only controls a badge and a filter toggle, never
# what gets collected.
MATCH_RENT_MIN = 6000
MATCH_RENT_MAX = 14000
MATCH_LAND_MIN = 4000     # m²

# ── property type ──────────────────────────────────────────────────────────
# The portals file every rural property under one "FARM" unit type, which
# flattens a real distinction: a chácara is a recreational plot, a sítio a small
# working property, a fazenda a farm proper. The words are right there in the
# title, so recover the distinction from it and fall back to the portal's type.
UNIT_TYPE_LABEL = {
    "FARM": "Chácara",
    "COUNTRY_HOUSE": "Chácara",
    "ALLOTMENT_LAND": "Terreno",
    "HOME": "Casa com terreno",
    "RESIDENTIAL_ALLOTMENT_LAND": "Terreno",
}
TITLE_TYPE_PATTERNS = [
    ("Fazenda", r"\bfazenda|\bharas\b"),
    ("Sítio",   r"\bs[ií]tio"),
    ("Chácara", r"\bch[aá]cara|\bran(cho|char)"),
    ("Terreno", r"\b(terreno|[aá]rea|lote|gleba)\b"),
]

# ── features ───────────────────────────────────────────────────────────────
# Two inputs per feature: the portal's amenity enum (authoritative when present)
# and a regex over title + description, which is where rural ads actually put
# this information. Both resolve to the same Portuguese label the page renders.
AMENITY_MAP = {
    "POOL": "Piscina", "PRIVATE_POOL": "Piscina", "SWIMMING_POOL": "Piscina",
    "BARBECUE_GRILL": "Área gourmet", "PIZZA_OVEN": "Área gourmet",
    "GOURMET_BALCONY": "Área gourmet", "GOURMET_SPACE": "Área gourmet",
    "PARTY_HALL": "Área gourmet",
    "FOOTBALL_FIELD": "Campo ou quadra", "SPORTS_COURT": "Campo ou quadra",
    "TENNIS_COURT": "Campo ou quadra", "PLAYGROUND": "Campo ou quadra",
    "FIREPLACE": "Lareira",
    "FURNISHED": "Mobiliada",
    "SECURITY_CAMERA": "Segurança", "ELECTRONIC_GATE": "Segurança",
    "24H_CONCIERGE": "Segurança", "GATED_COMMUNITY": "Segurança",
    "ALARM_SYSTEM": "Segurança", "SECURITY_24H": "Segurança",
    "INTERNET_ACCESS": "Internet",
    "AIR_CONDITIONING": "Ar-condicionado",
    "LAKE": "Lago ou represa", "ARTESIAN_WELL": "Poço ou nascente",
}
FEATURE_PATTERNS = [
    ("Piscina",          r"piscina"),
    ("Área gourmet",     r"[aá]rea gourmet|churrasqueira|forno de pizza|espa[çc]o gourmet|sal[ãa]o de festas"),
    ("Poço ou nascente", r"po[çc]o artesiano|\bpo[çc]o\b|nascente|mina d'?[aá]gua|[aá]gua de mina"),
    ("Lago ou represa",  r"\blago\b|lagoa|represa|a[çc]ude|tanque de peixe|pesqueiro"),
    ("Rio ou córrego",   r"\brio\b|c[oó]rrego|riacho|beira[- ]rio|cachoeira"),
    ("Casa de caseiro",  r"caseiro|casa de caseiro|casa do caseiro|zelador"),
    ("Pomar",            r"\bpomar\b|[aá]rvores frut[ií]feras|frut[ií]feras"),
    ("Baias ou haras",   r"\bbaia[s]?\b|cocheira|\bharas\b|estrebaria|para cavalos|piquete"),
    ("Campo ou quadra",  r"campo de futebol|quadra (poli)?esportiva|quadra de t[êe]nis"),
    ("Lareira",          r"lareira"),
    ("Mobiliada",        r"mobiliad[oa]|semi[- ]mobiliad[oa]"),
    ("Segurança",        r"condom[ií]nio fechado|portaria 24|seguran[çc]a 24|guarita"),
    ("Internet",         r"internet|fibra [oó]ptica|\bwi-?fi\b"),
    ("Energia solar",    r"energia solar|placas? solar|fotovoltaic"),
    ("Heliponto",        r"helipont"),
]
# Order the chips by how much they matter for somewhere to actually live,
# not by how often they appear.
FEATURE_ORDER = ["Piscina", "Poço ou nascente", "Lago ou represa", "Rio ou córrego",
                 "Área gourmet", "Casa de caseiro", "Pomar", "Baias ou haras",
                 "Campo ou quadra", "Lareira", "Mobiliada", "Segurança",
                 "Internet", "Ar-condicionado", "Energia solar", "Heliponto"]

_TYPE_RE = [(lab, re.compile(p, re.I)) for lab, p in TITLE_TYPE_PATTERNS]
_FEAT_RE = [(lab, re.compile(p, re.I)) for lab, p in FEATURE_PATTERNS]


def _norm(s):
    """Fold accents so 'sítio' and 'sitio' match the same pattern."""
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


def property_type(row):
    raw = (row.get("unit_type_raw") or "").upper()
    # HOME is the portal being literal about a field someone typed; the title is
    # more trustworthy about what the place actually is. For every other unit
    # type the portal and the title usually agree, and the title is more specific.
    text = _norm(row.get("title"))
    for label, rx in _TYPE_RE:
        if rx.search(text):
            return label
    return UNIT_TYPE_LABEL.get(raw, "Chácara")


def features(row):
    found = set()
    for a in row.get("amenities_raw") or []:
        lab = AMENITY_MAP.get(str(a).upper())
        if lab:
            found.add(lab)
    text = _norm(row.get("title")) + " " + _norm(row.get("description"))[:2500]
    for label, rx in _FEAT_RE:
        if rx.search(text):
            found.add(label)
    return [f for f in FEATURE_ORDER if f in found]


def is_match(row):
    """The badge: close to what is being replaced, on both rent and land."""
    rent, land = row.get("rent"), row.get("total_area")
    if not rent or not land:
        return 0
    return int(MATCH_RENT_MIN <= rent <= MATCH_RENT_MAX and land >= MATCH_LAND_MIN)


def price_per_m2(row):
    """Monthly rent per m² of land — the only fair way to compare these.

    Guarded against absurd areas: rural ads regularly quote the figure in
    hectares or alqueires while the field says m², and a 3-digit "area" would
    otherwise produce a headline number that is pure noise.
    """
    rent, land = row.get("rent"), row.get("total_area")
    if not rent or not land or land < 100:
        return None
    return round(rent / land, 3)


def classify(row):
    """Attach property_type, features, match and price_per_m2 (in place)."""
    row["property_type"] = property_type(row)
    row["features"] = features(row)
    row["match"] = is_match(row)
    row["price_per_m2"] = price_per_m2(row)
    return row
