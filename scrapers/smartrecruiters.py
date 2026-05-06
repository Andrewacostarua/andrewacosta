"""SmartRecruiters ATS scraper — public postings API, no auth required."""

import requests
from datetime import datetime
from .utils import is_match

BASE_URL = "https://api.smartrecruiters.com/v1/companies/{company}/postings"

FIRMS = [
    {"firm": "Ares Management", "company": "Ares", "tier": "reach", "track": "repe"},
]


def scrape(firm_config: dict) -> list[dict]:
    company = firm_config["company"]
    url     = BASE_URL.format(company=company)

    params = {"limit": 100, "offset": 0}
    resp   = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data   = resp.json()

    jobs = []
    today = datetime.utcnow().strftime("%Y-%m-%d")
    for posting in data.get("content", []):
        title = posting.get("name", "")
        if not is_match(title):
            continue
        job_id = f"sr-{company.lower()}-{posting['id']}"
        loc    = posting.get("location", {})
        jobs.append({
            "id":          job_id,
            "firm":        firm_config["firm"],
            "tier":        firm_config["tier"],
            "track":       firm_config["track"],
            "title":       title,
            "url":         f"https://jobs.smartrecruiters.com/{company}/{posting['id']}",
            "location":    f"{loc.get('city', '')}, {loc.get('region', '')}".strip(", "),
            "posted_date": posting.get("releasedDate", "")[:10] if posting.get("releasedDate") else "",
            "first_seen":  today,
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
            log_fn(f"[smartrecruiters] {firm['firm']}: {len(results)} match(es)")
            all_jobs.extend(results)
        except Exception as e:
            log_fn(f"[smartrecruiters] ERROR {firm['firm']} ({firm['company']}): {e}")
    return all_jobs
