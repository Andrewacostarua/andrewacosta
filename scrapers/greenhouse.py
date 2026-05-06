"""Greenhouse ATS scraper — uses the public JSON API, no auth required."""

import requests
from datetime import datetime
from .utils import is_match

BASE_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"

FIRMS = [
    # Slugs verified live against boards-api.greenhouse.io
    # Stonepeak → Ashby (playwright_scraper.py)
    # Blue Owl  → Workday (workday.py)
    # Ares      → SmartRecruiters (smartrecruiters.py)
    # Related   → iCIMS (icims.py)
    # Pretium   → Ashby (playwright_scraper.py)
    # Bridge    → Ashby (playwright_scraper.py)
    {"firm": "Apollo Global Management", "slug": "apollo",     "tier": "homerun", "track": "repe"},
    {"firm": "TPG Real Estate",          "slug": "tpgcareers", "tier": "reach",   "track": "repe"},
    # Berkadia confirmed Greenhouse (32 jobs live) — was wrongly listed as iCIMS in spec
    {"firm": "Berkadia",                 "slug": "berkadia",   "tier": "safety",  "track": "cm"},
]



def scrape(firm_config: dict) -> list[dict]:
    slug = firm_config["slug"]
    url = BASE_URL.format(slug=slug)
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for job in data.get("jobs", []):
        title = job.get("title", "")
        if not is_match(title):
            continue
        job_id = f"gh-{slug}-{job['id']}"
        jobs.append({
            "id":          job_id,
            "firm":        firm_config["firm"],
            "tier":        firm_config["tier"],
            "track":       firm_config["track"],
            "title":       title,
            "url":         job.get("absolute_url", ""),
            "location":    job.get("location", {}).get("name", ""),
            "posted_date": job.get("updated_at", "")[:10] if job.get("updated_at") else "",
            "first_seen":  datetime.utcnow().strftime("%Y-%m-%d"),
            "is_new":      False,
            "chance":      None,
            "salary":      None,
            "bonus":       None,
            "hours":       None,
        })
    return jobs


def scrape_all(log_fn=print) -> list[dict]:
    all_jobs = []
    for firm in FIRMS:
        try:
            results = scrape(firm)
            log_fn(f"[greenhouse] {firm['firm']}: {len(results)} match(es)")
            all_jobs.extend(results)
        except Exception as e:
            log_fn(f"[greenhouse] ERROR {firm['firm']} ({firm['slug']}): {e}")
    return all_jobs
