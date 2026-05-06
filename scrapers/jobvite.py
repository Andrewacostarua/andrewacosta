"""Jobvite ATS scraper — public job search API."""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from .utils import is_match

FIRMS = [
    {"firm": "W. P. Carey", "company_id": "wpccareers", "tier": "target", "track": "repe"},
]

BASE_URL = "https://jobs.jobvite.com/{company_id}/search"


def scrape(firm_config: dict) -> list[dict]:
    cid   = firm_config["company_id"]
    url   = BASE_URL.format(company_id=cid)
    today = datetime.utcnow().strftime("%Y-%m-%d")

    params = {"q": "analyst real estate", "l": ""}
    resp   = requests.get(url, params=params, timeout=15,
                          headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    jobs = []
    for item in soup.select("li.jv-job-list-name, div.position"):
        link = item.select_one("a")
        if not link:
            continue
        title = link.get_text(strip=True)
        if not is_match(title):
            continue
        href     = link.get("href", "")
        full_url = href if href.startswith("http") else f"https://jobs.jobvite.com{href}"
        job_id   = f"jv-{cid}-{href.rstrip('/').split('/')[-1]}"
        jobs.append({
            "id":          job_id,
            "firm":        firm_config["firm"],
            "tier":        firm_config["tier"],
            "track":       firm_config["track"],
            "title":       title,
            "url":         full_url,
            "location":    "",
            "posted_date": "",
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
            log_fn(f"[jobvite] {firm['firm']}: {len(results)} match(es)")
            all_jobs.extend(results)
        except Exception as e:
            log_fn(f"[jobvite] ERROR {firm['firm']} ({firm['company_id']}): {e}")
    return all_jobs
