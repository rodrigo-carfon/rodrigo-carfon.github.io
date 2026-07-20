# -*- coding: utf-8 -*-
"""Six public remote-job boards (no key). Adapted from the user's
fetch_international_jobs.py — the eligibility/profile filters are dropped; we keep
every posting and classify later. Each fetch_* returns normalized job dicts.
"""
import time
from ._http import get_json
from ._common import strip_html, iso_date, work_model_pt, job

MARKET = "Global remote"


def fetch_remotive():
    out = []
    for cat in ("data", "marketing", "all-others"):
        d = get_json(f"https://remotive.com/api/remote-jobs?category={cat}")
        for j in d.get("jobs", []):
            out.append(job(
                "remotive", j.get("id") or j.get("url"),
                title=j.get("title", ""), company=j.get("company_name", ""),
                url=j.get("url", ""), work_model="remoto",
                country=j.get("candidate_required_location", "") or "", market=MARKET,
                published_date=iso_date(j.get("publication_date")),
                skills=[t for t in (j.get("tags") or []) if t][:8],
                description=strip_html(j.get("description", "")),
                categories=[j.get("category", "")] if j.get("category") else [],
            ))
        time.sleep(0.3)
    return out


def fetch_jobicy():
    d = get_json("https://jobicy.com/api/v2/remote-jobs?count=200")
    out = []
    for j in d.get("jobs", []):
        ind = j.get("jobIndustry")
        cats = ind if isinstance(ind, list) else ([ind] if ind else [])
        out.append(job(
            "jobicy", j.get("id") or j.get("url"),
            title=j.get("jobTitle", ""), company=j.get("companyName", ""),
            url=j.get("url", ""), work_model="remoto",
            country=j.get("jobGeo", "") or "", market=MARKET,
            published_date=iso_date(j.get("pubDate")),
            description=strip_html((j.get("jobExcerpt", "") or "")),
            categories=[str(c) for c in cats if c],
        ))
    return out


def fetch_remoteok():
    d = get_json("https://remoteok.com/api")
    out = []
    for j in d:
        if not isinstance(j, dict) or not j.get("id"):
            continue
        smin, smax = j.get("salary_min"), j.get("salary_max")
        out.append(job(
            "remoteok", j.get("id"),
            title=j.get("position", ""), company=j.get("company", ""),
            url=j.get("url") or f"https://remoteok.com/remote-jobs/{j.get('id')}",
            work_model="remoto", country="", market=MARKET,
            salary_min=smin if smin else None,
            salary_max=smax if smax else None,
            salary_currency="USD" if (smin or smax) else None,
            published_date=iso_date(j.get("date")),
            skills=[t for t in (j.get("tags") or []) if t][:8],
            description=strip_html(j.get("description", "")),
        ))
    return out


def fetch_himalayas():
    out = []
    for off in (0, 50, 100, 150):
        d = get_json(f"https://himalayas.app/jobs/api?limit=50&offset={off}")
        jobs = d.get("jobs", [])
        for j in jobs:
            restr = j.get("locationRestrictions") or []
            out.append(job(
                "himalayas", j.get("guid") or j.get("title"),
                title=j.get("title", ""), company=j.get("companyName", ""),
                url=j.get("applicationLink") or j.get("guid", ""),
                work_model="remoto",
                country=", ".join(restr) if isinstance(restr, list) else str(restr),
                market=MARKET,
                published_date=iso_date(j.get("pubDate")),
                skills=[t for t in (j.get("categories") or []) if t][:8],
                description=strip_html(j.get("excerpt", "")),
            ))
        if len(jobs) < 50:
            break
        time.sleep(0.3)
    return out


def fetch_workingnomads():
    d = get_json("https://www.workingnomads.com/api/exposed_jobs/")
    out = []
    for j in (d if isinstance(d, list) else []):
        out.append(job(
            "workingnomads", j.get("url"),
            title=j.get("title", ""), company=j.get("company_name", ""),
            url=j.get("url", ""), work_model=work_model_pt(raw=j.get("location")),
            country=j.get("location", "") or "", market=MARKET,
            published_date=iso_date(j.get("pub_date")),
            description=strip_html(j.get("description", "")),
            categories=[j.get("category_name", "")] if j.get("category_name") else [],
        ))
    return out


def fetch_arbeitnow():
    out = []
    for page in (1, 2, 3):
        d = get_json(f"https://www.arbeitnow.com/api/job-board-api?page={page}")
        data = d.get("data", [])
        for j in data:
            out.append(job(
                "arbeitnow", j.get("slug") or j.get("url"),
                title=j.get("title", ""), company=j.get("company_name", ""),
                url=j.get("url", ""),
                work_model="remoto" if j.get("remote") else work_model_pt(raw=j.get("location")),
                country=j.get("location", "") or "", market=MARKET,
                published_date=iso_date(j.get("created_at")),
                skills=[t for t in (j.get("tags") or []) if t][:8],
                description=strip_html(j.get("description", "")),
            ))
        if not data:
            break
        time.sleep(0.3)
    return out


ADAPTERS = [fetch_remotive, fetch_jobicy, fetch_remoteok,
            fetch_himalayas, fetch_workingnomads, fetch_arbeitnow]
