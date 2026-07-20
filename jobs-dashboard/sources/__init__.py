# -*- coding: utf-8 -*-
"""Source registry. Each entry is (name, fetch_callable) returning normalized jobs.

All endpoints are public and key-free. (Adzuna, which needed a free key, was left
out by choice — its adapter can be re-added later if a key is ever provided.)
"""
from . import gupy, themuse, remote_boards, ats_boards, wwr

REGISTRY = [
    ("gupy", gupy.fetch),
    ("themuse", themuse.fetch),
    ("remotive", remote_boards.fetch_remotive),
    ("jobicy", remote_boards.fetch_jobicy),
    ("remoteok", remote_boards.fetch_remoteok),
    ("himalayas", remote_boards.fetch_himalayas),
    ("workingnomads", remote_boards.fetch_workingnomads),
    ("arbeitnow", remote_boards.fetch_arbeitnow),
    ("weworkremotely", wwr.fetch),
    ("greenhouse", ats_boards.fetch_greenhouse),
    ("lever", ats_boards.fetch_lever),
    ("ashby", ats_boards.fetch_ashby),
]
