# -*- coding: utf-8 -*-
"""Gupy (Brazil) — public JSON endpoint, no key.

Adapted from the user's fetch_gupy_jobs_lote4.py. The profile/adherence filtering
is intentionally dropped: this project keeps every job and only classifies it.
Endpoint: employability-portal.gupy.io/api/v1/jobs?jobName=&limit=&offset=
"""
import os
import time
import urllib.parse
from ._http import get_json
from ._common import strip_html, iso_date, work_model_pt, job

API = "https://employability-portal.gupy.io/api/v1/jobs"
HEADERS = {"Origin": "https://portal.gupy.io", "Referer": "https://portal.gupy.io/"}

# A broad sweep of the Brazilian market — not tuned to any single profile.
TERMS = [
    "analista de dados", "engenheiro de dados", "analista de bi", "business intelligence",
    "data analyst", "data engineer", "data science", "cientista de dados",
    "desenvolvedor", "engenheiro de software", "programador", "backend", "frontend",
    "product manager", "produto", "designer", "ux",
    "marketing", "growth", "vendas", "comercial", "sdr",
    "financeiro", "contábil", "controladoria", "rh", "recursos humanos",
    "customer success", "suporte", "atendimento", "operações", "logística",
    "estágio", "jovem aprendiz", "analista", "coordenador", "gerente",
]

PAGE = 40
MAX_OFFSET = 120  # up to 4 pages per term


def fetch():
    # GUPY_MAX_TERMS caps the sweep (handy for quick local runs / CI tuning).
    limit = int(os.environ.get("GUPY_MAX_TERMS") or len(TERMS))
    seen, out = set(), []
    for term in TERMS[:limit]:
        q = urllib.parse.quote(term)  # encode accents/spaces → valid ASCII URL
        for offset in range(0, MAX_OFFSET + 1, PAGE):
            url = f"{API}?jobName={q}&limit={PAGE}&offset={offset}"
            data = get_json(url, headers=HEADERS).get("data", [])
            for j in data:
                jid = j.get("id")
                if jid in seen:
                    continue
                seen.add(jid)
                remote = bool(j.get("isRemoteWork"))
                skills = [s.get("name", "") if isinstance(s, dict) else str(s)
                          for s in (j.get("skills") or [])]
                out.append(job(
                    "gupy", jid,
                    title=j.get("name", ""),
                    company=j.get("careerPageName", ""),
                    url=j.get("jobUrl", ""),
                    work_model=work_model_pt(remote, j.get("workplaceType")),
                    city=j.get("city", "") or "",
                    state=j.get("state", "") or "",
                    country="BR", market="BR",
                    published_date=iso_date(j.get("publishedDate")),
                    skills=[s for s in skills if s],
                    description=strip_html(j.get("description", "")),
                ))
            if len(data) < PAGE:
                break
            time.sleep(0.4)
        time.sleep(0.3)
    return out
