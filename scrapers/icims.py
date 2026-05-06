"""iCIMS ATS scraper — public job search API."""

import requests
from datetime import datetime
from .utils import is_match

# Each firm needs: subdomain used in iCIMS URL, and the iCIMS customer ID
# URL pattern: https://{subdomain}.icims.com/jobs/search?in_jdsearch=analyst&ss=1&searchLocation=
FIRMS = [
    # Walker & Dunlop → Workday (workday.py), Berkadia → Greenhouse (greenhouse.py)
    # Hines iCIMS requires auth — moved to playwright_scraper.py
    {"firm": "Related Companies",  "subdomain": "careers-related",  "tier": "reach",   "track": "repe"},
]


def scrape(firm_config: dict) -> list[dict]:
    subdomain = firm_config["subdomain"]
    # iCIMS has a JSON search API
    url = f"https://{subdomain}.icims.com/jobs/search"
    params = {
        "in_jdsearch": "analyst real estate",
        "ss":          1,
        "pr":          1,
        "in_iframe":   1,
        "hashed":      -1332571853,
    }
    headers = {
        "Accept":     "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    }
    resp = requests.get(url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()

    # iCIMS returns HTML by default; parse it
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(resp.text, "lxml")
    today = datetime.utcnow().strftime("%Y-%m-%d")

    jobs = []
    for item in soup.select("div.iCIMS_JobsTable div.iCIMS_Expandable_Item, li.icims-job"):
        title_el = item.select_one("h2, .iCIMS_JobTitle, .job-title")
        link_el  = item.select_one("a[href*='/jobs/']")
        if not title_el or not link_el:
            continue
        title = title_el.get_text(strip=True)
        if not is_match(title):
            continue
        href   = link_el.get("href", "")
        full_url = href if href.startswith("http") else f"https://{subdomain}.icims.com{href}"
        job_id = f"icims-{subdomain}-{href.rstrip('/').split('/')[-1]}"
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
            log_fn(f"[icims] {firm['firm']}: {len(results)} match(es)")
            all_jobs.extend(results)
        except Exception as e:
            log_fn(f"[icims] ERROR {firm['firm']} ({firm['subdomain']}): {e}")
    return all_jobs
