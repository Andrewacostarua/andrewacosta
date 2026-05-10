"""LinkedIn guest-API scraper — covers all 50 firms including bot-protected ones.

LinkedIn's /jobs-guest/ endpoint is public (no auth) and covers every firm
that posts there, including Goldman, Morgan Stanley, and Blackstone which
block headless-browser scrapers via Cloudflare. Company IDs are stable.
"""

import time
import requests
from bs4 import BeautifulSoup
from .utils import is_match, is_target_location

# LinkedIn company IDs — stable internal identifiers, not URLs.
# Each maps firm display name → {linkedin_id, tier, track}.
# IDs verified against linkedin.com/company/<slug> pages.
FIRMS = {
    # ── Homerun ──────────────────────────────────────────────────────────
    "Goldman Sachs":            {"id": "1441",      "tier": "homerun", "track": "ib"},
    "Morgan Stanley":           {"id": "1550",      "tier": "homerun", "track": "ib"},
    "Blackstone":               {"id": "16140",     "tier": "homerun", "track": "repe"},
    "KKR":                      {"id": "2197",      "tier": "homerun", "track": "repe"},
    "Apollo Global Management": {"id": "153457",    "tier": "homerun", "track": "repe"},
    "Carlyle Group":            {"id": "3009",      "tier": "homerun", "track": "repe"},
    "Brookfield Asset Mgmt":   {"id": "78340",     "tier": "homerun", "track": "repe"},
    "BlackRock":                {"id": "3090",      "tier": "homerun", "track": "repe"},
    "Stonepeak":                {"id": "19131555",  "tier": "homerun", "track": "infra"},
    # ── Reach ────────────────────────────────────────────────────────────
    "Ares Management":          {"id": "8803",      "tier": "reach",   "track": "repe"},
    "Starwood Capital Group":   {"id": "8814",      "tier": "reach",   "track": "repe"},
    "TPG":                      {"id": "3080952",   "tier": "reach",   "track": "repe"},
    "Cerberus Capital Mgmt":   {"id": "11879",     "tier": "reach",   "track": "repe"},
    "EQT":                      {"id": "167704",    "tier": "reach",   "track": "repe"},
    "Tishman Speyer":           {"id": "9140",      "tier": "reach",   "track": "repe"},
    "Related Companies":        {"id": "9443",      "tier": "reach",   "track": "repe"},
    "Rockpoint Group":          {"id": "19668",     "tier": "reach",   "track": "repe"},
    "Pretium Partners":         {"id": "2586429",   "tier": "reach",   "track": "repe"},
    "Dune Real Estate Partners":{"id": "3158630",   "tier": "reach",   "track": "repe"},
    "Harrison Street":          {"id": "47996",     "tier": "reach",   "track": "repe"},
    "Eastdil Secured":          {"id": "19206",     "tier": "reach",   "track": "cm"},
    # ── Target ───────────────────────────────────────────────────────────
    "Blue Owl Capital":         {"id": "71828392",  "tier": "target",  "track": "repe"},
    "W. P. Carey":              {"id": "3436",      "tier": "target",  "track": "repe"},
    "Digital Realty":           {"id": "11600",     "tier": "target",  "track": "repe"},
    "I Squared Capital":        {"id": "2737253",   "tier": "target",  "track": "infra"},
    "AEW Capital Management":   {"id": "9218",      "tier": "target",  "track": "repe"},
    "LaSalle Investment Mgmt":  {"id": "9287",      "tier": "target",  "track": "repe"},
    "BentallGreenOak":          {"id": "823421",    "tier": "target",  "track": "repe"},
    "Clarion Partners":         {"id": "32681",     "tier": "target",  "track": "repe"},
    "Hines":                    {"id": "3255",      "tier": "target",  "track": "repe"},
    "Nuveen":                   {"id": "11896",     "tier": "target",  "track": "repe"},
    "Bridge Investment Group":  {"id": "2396033",   "tier": "target",  "track": "repe"},
    "Heitman":                  {"id": "20140",     "tier": "target",  "track": "repe"},
    "Walton Street Capital":    {"id": "27153",     "tier": "target",  "track": "repe"},
    "TA Realty":                {"id": "12780",     "tier": "target",  "track": "repe"},
    "Somera Road":              {"id": "10405518",  "tier": "target",  "track": "repe"},
    "Jefferies":                {"id": "2945",      "tier": "target",  "track": "ib"},
    # ── Safety ───────────────────────────────────────────────────────────
    "JLL":                      {"id": "1180",      "tier": "safety",  "track": "cm"},
    "CBRE":                     {"id": "1267",      "tier": "safety",  "track": "cm"},
    "Cushman & Wakefield":      {"id": "4027",      "tier": "safety",  "track": "cm"},
    "Walker & Dunlop":          {"id": "47420",     "tier": "safety",  "track": "cm"},
    "Marcus & Millichap":       {"id": "4808",      "tier": "safety",  "track": "cm"},
    "Wells Fargo":              {"id": "3525",      "tier": "safety",  "track": "ib"},
    "KeyBank":                  {"id": "3543",      "tier": "safety",  "track": "cm"},
    "UBS":                      {"id": "2660",      "tier": "safety",  "track": "ib"},
    "Stifel":                   {"id": "4928",      "tier": "safety",  "track": "ib"},
    "Revantage":                {"id": "18907418",  "tier": "safety",  "track": "repe"},
    "Fidelity Investments":     {"id": "1138",      "tier": "safety",  "track": "repe"},
    "State Street":             {"id": "1856",      "tier": "safety",  "track": "repe"},
    "Berkadia":                 {"id": "10509",     "tier": "safety",  "track": "cm"},
}

_BASE = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _fetch_page(company_id: str, start: int = 0) -> list[dict]:
    """Fetch one page (25 listings) from LinkedIn's guest jobs API."""
    params = {
        "keywords":  "analyst associate",
        "f_C":       company_id,
        "location":  "United States",
        "f_TPR":     "r7776000",   # posted in last 90 days (firms tag FT roles inconsistently)
        "start":     start,
    }
    try:
        r = requests.get(_BASE, params=params, headers=_HEADERS, timeout=15)
        if r.status_code == 429:
            return []   # rate-limited — skip, next run will catch it
        if r.status_code != 200:
            return []
    except requests.RequestException:
        return []

    soup = BeautifulSoup(r.text, "lxml")
    results = []

    for card in soup.find_all("div", class_="base-card"):
        title_el    = card.find(["h3", "span"], class_="base-search-card__title")
        location_el = card.find("span", class_="job-search-card__location")
        link_el     = card.find("a", class_="base-card__full-link")
        time_el     = card.find("time")

        if not (title_el and link_el):
            continue

        title    = title_el.get_text(strip=True)
        location = location_el.get_text(strip=True) if location_el else ""
        href     = (link_el.get("href") or "").split("?")[0].strip()
        posted   = time_el.get("datetime", "") if time_el else ""

        # Extract LinkedIn job ID from URL for stable dedup key
        parts  = [p for p in href.rstrip("/").split("/") if p]
        job_id = parts[-1] if parts else href

        results.append({
            "title":    title,
            "location": location,
            "url":      href,
            "job_id":   job_id,
            "posted":   posted,
        })

    return results


def _scrape_firm(name: str, info: dict, log_fn) -> list[dict]:
    company_id = info["id"]
    raw        = _fetch_page(company_id, start=0)

    # Grab a second page for large employers (Goldman, JLL, CBRE, etc.)
    if len(raw) >= 25:
        time.sleep(0.8)
        raw += _fetch_page(company_id, start=25)

    matched = []
    for item in raw:
        if not is_match(item["title"]):
            continue
        if not is_target_location(item["location"]):
            continue
        matched.append({
            "id":          f"li-{item['job_id']}",
            "firm":        name,
            "tier":        info["tier"],
            "track":       info["track"],
            "title":       item["title"],
            "url":         item["url"],
            "location":    item["location"],
            "posted_date": item["posted"],
            "first_seen":  None,   # set by orchestrator
            "is_new":      False,  # set by orchestrator
            "source":      "linkedin",
            "salary":      None,
            "bonus":       None,
            "chance":      None,
            "hours":       None,
        })

    log_fn(f"[linkedin] {name}: {len(matched)} match(es) (saw {len(raw)} listings)")
    return matched


def scrape_all(log_fn=print) -> list[dict]:
    jobs = []
    for name, info in FIRMS.items():
        try:
            jobs.extend(_scrape_firm(name, info, log_fn))
        except Exception as e:
            log_fn(f"[linkedin] ERROR {name}: {e}")
        time.sleep(1.2)   # be a polite guest — 1.2s between firms
    return jobs
