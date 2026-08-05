# -*- coding: utf-8 -*-
"""Source registry. Each entry is (name, fetch_callable) returning normalized listings.

Same shape as jobs-dashboard/sources/__init__.py, and the same contract: the
pipeline calls each entry in isolation, so one portal changing its API never
aborts the run.

One entry today, covering the three largest portals in Brazil at once: VivaReal,
ZAP and OLX share a single inventory behind one endpoint (see grupozap.py). It
carries its own VivaReal → ZAP failover internally, because those two are the
same data and listing them as two registry entries would just collect it twice.

Candidates for later, all confirmed reachable but none yet adapted: Chaves na Mão
(sitemap + JSON-LD), Imovelweb, and the specialist rural agencies (Casa na
Floresta, Canário, LC Fazendas). Mercado Livre's API needs OAuth and is out.
Adding one is a new module plus one line here — nothing else changes.
"""
from . import grupozap

REGISTRY = [
    ("grupozap", grupozap.fetch),
]
