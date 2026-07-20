# -*- coding: utf-8 -*-
"""Derive área-de-atuação and seniority for a normalized job.

Resolution order for both:
  1. structured hints the source already gives (The Muse levels[]/categories[],
     other portals' category strings), then
  2. keyword/regex classification on the title (and description as a tiebreak).
Reuses the seniority regexes and the role keyword idea from the user's existing
fetchers, generalized off any single profile.
"""
import re
import unicodedata

# ── Seniority ──────────────────────────────────────────────────────────────
SENIORITY_PATTERNS = [
    ("estágio",         r"est[aá]gi|trainee|intern(ship)?|aprendiz|\bstage\b"),
    ("júnior",          r"j[uú]nior|\bjr\b|entry[- ]?level|\bi\b\s*$"),
    ("pleno",           r"pleno|\bpl\b|mid[- ]?level|\bmid\b|\bii\b\s*$"),
    ("sênior",          r"s[eê]nior|\bsr\b|\bsenior\b|\biii\b\s*$"),
    ("gestão/especialista", r"especialista|coordenador|gerente|\blead\b|principal|"
                            r"staff|head|diretor|director|manager|supervisor|\bvp\b|chefe"),
]
MUSE_LEVEL = {
    "internship": "estágio", "entry level": "júnior", "mid level": "pleno",
    "senior level": "sênior", "management": "gestão/especialista",
}

# ── Área de atuação ────────────────────────────────────────────────────────
# Order matters — first match wins on ties handled by scoring below.
AREA_KEYWORDS = {
    "dados": ["analista de dados", "cientista de dados", "data analyst", "data scientist",
              "data engineer", "engenheiro de dados", "business intelligence", " bi ",
              "power bi", "analytics", "machine learning", "estatística", "\\betl\\b",
              "\\bsql\\b", "dados", "\\bdata\\b", "big data", "data science"],
    "engenharia de software": ["desenvolvedor", "developer", "software engineer",
              "engenheiro de software", "backend", "back-end", "frontend", "front-end",
              "full stack", "fullstack", "full-stack", "programador", "devops", "\\bsre\\b",
              "\\bqa\\b", "quality assurance", "tester", "mobile", "\\bandroid\\b", "\\bios\\b",
              "\\bjava\\b", "python", "react", "node", "\\b.net\\b", "cloud", "infra"],
    "produto": ["product manager", "gerente de produto", "product owner", "\\bpo\\b",
                "\\bpm\\b", "produto", "product designer"],
    "design": ["designer", "\\bux\\b", "\\bui\\b", "ux/ui", "user experience", "design"],
    "marketing": ["marketing", "growth", "\\bseo\\b", "mídia", "\\bads\\b", "conteúdo",
                  "social media", "brand", "comunicação", "publicidade"],
    "vendas": ["vendas", "\\bsales\\b", "comercial", "\\bsdr\\b", "\\bbdr\\b",
               "account executive", "business development", "pré-vendas", "representante"],
    "financeiro": ["financeiro", "finance", "contábil", "contabil", "controladoria",
                   "accounting", "fp&a", "tesouraria", "fiscal", "auditor"],
    "operações": ["operações", "operations", "logística", "supply", "\\bops\\b",
                  "processos", "\\bpcp\\b", "produção"],
    "rh": ["recursos humanos", "\\brh\\b", "people", "talent", "recrutador", "recruiter",
           "human resources", "\\bdp\\b", "departamento pessoal"],
    "atendimento": ["customer success", "customer support", "customer experience",
                    "suporte", "atendimento", "\\bcs\\b", "success", "help desk", "helpdesk"],
}
# Map portal category strings → our buckets
CATEGORY_MAP = {
    "data": "dados", "data science": "dados", "analytics": "dados",
    "software development": "engenharia de software", "development": "engenharia de software",
    "engineering": "engenharia de software", "devops and sysadmin": "engenharia de software",
    "system administration": "engenharia de software", "qa": "engenharia de software",
    "product": "produto", "design": "design", "marketing": "marketing",
    "sales": "vendas", "sales and marketing": "vendas", "finance": "financeiro",
    "finance and legal": "financeiro", "human resources": "rh", "hr": "rh",
    "customer service": "atendimento", "customer support": "atendimento",
    "all others": "outros", "business": "outros", "management": "outros",
}

_AREA_RE = {area: [re.compile(k, re.I) for k in kws] for area, kws in AREA_KEYWORDS.items()}


def _norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return s.lower()


def seniority(job):
    for lvl in (job.get("levels") or []):
        m = MUSE_LEVEL.get(lvl.strip().lower())
        if m:
            return m
    t = " " + (job.get("title") or "").lower() + " "
    for name, pat in SENIORITY_PATTERNS[::-1]:  # check senior/gestão before júnior etc.
        if re.search(pat, t, re.I):
            return name
    return "n/d"


def area(job):
    # 1) structured category from the portal (be tolerant of odd shapes)
    for cat in (job.get("categories") or []):
        if not isinstance(cat, str):
            cat = " ".join(map(str, cat)) if isinstance(cat, list) else str(cat)
        m = CATEGORY_MAP.get(cat.strip().lower())
        if m:
            return m
    # 2) keyword scoring on title (weighted) + description (light)
    title = " " + (job.get("title") or "") + " "
    desc = (job.get("description") or "")[:500]
    best, best_score = "outros", 0
    for a, regexes in _AREA_RE.items():
        score = sum(3 for r in regexes if r.search(title))
        score += sum(1 for r in regexes if r.search(desc))
        if score > best_score:
            best, best_score = a, score
    return best if best_score >= 3 else "outros"


def classify(job):
    """Attach 'area' and 'seniority' to a normalized job dict (in place)."""
    job["area"] = area(job)
    job["seniority"] = seniority(job)
    return job
