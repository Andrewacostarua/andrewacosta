"""Lever ATS scraper — public JSON API, no auth required."""

import requests
from datetime import datetime
from .utils import is_match

BASE_URL = "https://api.lever.co/v0/postings/{slug}?mode=json"

FIRMS: list[dict] = [
    # Add Lever firms here as they are discovered, e.g.:
    # {"firm": "Example Firm", "slug": "example-firm", "tier": "target", "track": "repe"},
]



def scrape(firm_config: dict) -> list[dict]:
    slug = firm_config["slug"]
    url  = BASE_URL.format(slug=slug)
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for posting in data:
        title = posting.get("text", "")
        if not is_match(title):
            continue
        job_id = f"lv-{slug}-{posting['id']}"
        jobs.append({
            "id":          job_id,
            "firm":        firm_config["firm"],
            "tier":        firm_config["tier"],
            "track":       firm_config["track"],
            "title":       title,
            "url":         posting.get("hostedUrl", ""),
            "location":    posting.get("categories", {}).get("location", ""),
            "posted_date": datetime.utcfromtimestamp(posting["createdAt"] / 1000).strftime("%Y-%m-%d") if posting.get("createdAt") else "",
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
            log_fn(f"[lever] {firm['firm']}: {len(results)} match(es)")
            all_jobs.extend(results)
        except Exception as e:
            log_fn(f"[lever] ERROR {firm['firm']} ({firm['slug']}): {e}")
    return all_jobs
