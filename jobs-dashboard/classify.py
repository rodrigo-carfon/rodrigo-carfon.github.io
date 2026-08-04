# -*- coding: utf-8 -*-
"""Derive area of work and seniority for a normalized job.

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
# Labels are the strings the dashboard renders — keep them English; the patterns
# stay bilingual because the titles they match come from BR and global portals.
SENIORITY_PATTERNS = [
    ("internship",      r"est[aá]gi|trainee|intern(ship)?|aprendiz|\bstage\b"),
    ("junior",          r"j[uú]nior|\bjr\b|entry[- ]?level|\bi\b\s*$"),
    ("mid-level",       r"pleno|\bpl\b|mid[- ]?level|\bmid\b|\bii\b\s*$"),
    ("senior",          r"s[eê]nior|\bsr\b|\bsenior\b|\biii\b\s*$"),
    ("lead/management", r"especialista|coordenador|gerente|\blead\b|principal|"
                        r"staff|head|diretor|director|manager|supervisor|\bvp\b|chefe"),
]
MUSE_LEVEL = {
    "internship": "internship", "entry level": "junior", "mid level": "mid-level",
    "senior level": "senior", "management": "lead/management",
}

# ── Area of work ───────────────────────────────────────────────────────────
# Order matters — first match wins on ties handled by scoring below.
AREA_KEYWORDS = {
    "data": ["analista de dados", "cientista de dados", "data analyst", "data scientist",
              "data engineer", "engenheiro de dados", "business intelligence", " bi ",
              "power bi", "analytics", "machine learning", "estatística", "\\betl\\b",
              "\\bsql\\b", "dados", "\\bdata\\b", "big data", "data science"],
    "software engineering": ["desenvolvedor", "developer", "software engineer",
              "engenheiro de software", "backend", "back-end", "frontend", "front-end",
              "full stack", "fullstack", "full-stack", "programador", "devops", "\\bsre\\b",
              "\\bqa\\b", "quality assurance", "tester", "mobile", "\\bandroid\\b", "\\bios\\b",
              "\\bjava\\b", "python", "react", "node", "\\b.net\\b", "cloud", "infra"],
    "product": ["product manager", "gerente de produto", "product owner", "\\bpo\\b",
                "\\bpm\\b", "produto", "product designer"],
    "design": ["designer", "\\bux\\b", "\\bui\\b", "ux/ui", "user experience", "design"],
    "marketing": ["marketing", "growth", "\\bseo\\b", "mídia", "\\bads\\b", "conteúdo",
                  "social media", "brand", "comunicação", "publicidade"],
    "sales": ["vendas", "\\bsales\\b", "comercial", "\\bsdr\\b", "\\bbdr\\b",
              "account executive", "business development", "pré-vendas", "representante"],
    "finance": ["financeiro", "finance", "contábil", "contabil", "controladoria",
                "accounting", "fp&a", "tesouraria", "fiscal", "auditor"],
    "operations": ["operações", "operations", "logística", "supply", "\\bops\\b",
                   "processos", "\\bpcp\\b", "produção"],
    "hr": ["recursos humanos", "\\brh\\b", "people", "talent", "recrutador", "recruiter",
           "human resources", "\\bdp\\b", "departamento pessoal"],
    "customer support": ["customer success", "customer support", "customer experience",
                         "suporte", "atendimento", "\\bcs\\b", "success", "help desk", "helpdesk"],
}
# Map portal category strings → our buckets
CATEGORY_MAP = {
    "data": "data", "data science": "data", "analytics": "data",
    "software development": "software engineering", "development": "software engineering",
    "engineering": "software engineering", "devops and sysadmin": "software engineering",
    "system administration": "software engineering", "qa": "software engineering",
    "product": "product", "design": "design", "marketing": "marketing",
    "sales": "sales", "sales and marketing": "sales", "finance": "finance",
    "finance and legal": "finance", "human resources": "hr", "hr": "hr",
    "customer service": "customer support", "customer support": "customer support",
    "all others": "other", "business": "other", "management": "other",
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
    for name, pat in SENIORITY_PATTERNS[::-1]:  # check senior/lead before junior etc.
        if re.search(pat, t, re.I):
            return name
    return "n/a"


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
    best, best_score = "other", 0
    for a, regexes in _AREA_RE.items():
        score = sum(3 for r in regexes if r.search(title))
        score += sum(1 for r in regexes if r.search(desc))
        if score > best_score:
            best, best_score = a, score
    return best if best_score >= 3 else "other"


def classify(job):
    """Attach 'area' and 'seniority' to a normalized job dict (in place)."""
    job["area"] = area(job)
    job["seniority"] = seniority(job)
    return job
