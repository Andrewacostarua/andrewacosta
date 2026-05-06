"""Workday ATS scraper — POST to the internal search API.

All entries verified live. Firms whose slugs couldn't be confirmed are
handled by playwright_scraper.py instead.
"""

import re
import requests
from datetime import datetime, timedelta
from .utils import is_match

# Each entry: subdomain, jobsite slug, and wd version (wd1 or wd5)
FIRMS = [
    # Homerun
    {"firm": "BlackRock Real Assets", "subdomain": "blackrock", "jobsite": "BlackRock_Professional", "wdver": "wd1", "tier": "homerun", "track": "repe"},
    # KKR → 422 (unknown jobsite), Carlyle → 401 (auth) — both in playwright_scraper.py
    # Target
    {"firm": "Blue Owl Capital",      "subdomain": "blueowl",  "jobsite": "blueowl",              "wdver": "wd1", "tier": "target",  "track": "repe"},
    {"firm": "LaSalle Investment",    "subdomain": "jll",      "jobsite": "lasallecareers",        "wdver": "wd1", "tier": "target",  "track": "repe"},
    {"firm": "Nuveen Real Estate",    "subdomain": "tiaa",     "jobsite": "Search",                "wdver": "wd1", "tier": "target",  "track": "repe"},
    # W.P. Carey → Jobvite (jobvite.py), Digital Realty → Oracle HCM, BentallGreenOak → unknown
    # Safety
    {"firm": "JLL Capital Markets",   "subdomain": "jll",      "jobsite": "jllcareers",            "wdver": "wd1", "tier": "safety",  "track": "cm"},
    {"firm": "Cushman & Wakefield",   "subdomain": "cw",       "jobsite": "External",              "wdver": "wd1", "tier": "safety",  "track": "cm"},
    {"firm": "KeyBank RE",            "subdomain": "keybank",  "jobsite": "External_Career_Site",  "wdver": "wd5", "tier": "safety",  "track": "cm"},
    # CBRE → custom domain (playwright), Wells Fargo → unknown slug, UBS → unknown, State Street → unknown
    # Walker & Dunlop confirmed Workday (12 jobs live) — was wrongly listed as iCIMS in spec
    {"firm": "Walker & Dunlop",       "subdomain": "walkerdunlop", "jobsite": "WD",   "wdver": "wd1", "tier": "safety",  "track": "cm"},
]

def _build_url(subdomain: str, jobsite: str, wdver: str) -> str:
    return f"https://{subdomain}.{wdver}.myworkdayjobs.com/wday/cxs/{subdomain}/{jobsite}/jobs"


def _parse_posted_date(raw: str) -> str:
    """Convert Workday relative strings like 'Posted 6 Days Ago' to YYYY-MM-DD."""
    if not raw:
        return ""
    today = datetime.utcnow().date()
    raw_l = raw.lower()
    if "today" in raw_l:
        return str(today)
    m = re.search(r"(\d+)\s*day", raw_l)
    if m:
        return str(today - timedelta(days=int(m.group(1))))
    m = re.search(r"(\d+)\s*month", raw_l)
    if m:
        return str(today - timedelta(days=int(m.group(1)) * 30))
    if "30+" in raw_l or "month" in raw_l:
        return str(today - timedelta(days=30))
    return ""


def scrape(firm_config: dict) -> list[dict]:
    subdomain = firm_config["subdomain"]
    jobsite   = firm_config["jobsite"]
    wdver     = firm_config.get("wdver", "wd1")
    url       = _build_url(subdomain, jobsite, wdver)

    payload = {
        "appliedFacets": {},
        "limit": 20,
        "offset": 0,
        "searchText": "analyst real estate",
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    base_url = f"https://{subdomain}.{wdver}.myworkdayjobs.com"
    for posting in data.get("jobPostings", []):
        title = posting.get("title", "")
        if not is_match(title):
            continue
        ext_path = posting.get("externalPath", "")
        job_id   = f"wd-{subdomain}-{ext_path.rstrip('/').split('/')[-1]}"
        jobs.append({
            "id":          job_id,
            "firm":        firm_config["firm"],
            "tier":        firm_config["tier"],
            "track":       firm_config["track"],
            "title":       title,
            "url":         base_url + ext_path,
            "location":    posting.get("locationsText", ""),
            "posted_date": _parse_posted_date(posting.get("postedOn", "")),
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
            log_fn(f"[workday] {firm['firm']}: {len(results)} match(es)")
            all_jobs.extend(results)
        except Exception as e:
            log_fn(f"[workday] ERROR {firm['firm']} ({firm['subdomain']}): {e}")
    return all_jobs
