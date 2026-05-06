"""Playwright scraper for JS-heavy and custom career pages."""

import asyncio
from datetime import datetime
from bs4 import BeautifulSoup
from .utils import is_match

# Playwright is imported lazily so the module loads even if not installed
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

FIRMS = [
    # Homerun tier
    {"firm": "Blackstone (BREP)",     "url": "https://careers.smartrecruiters.com/Blackstone",          "tier": "homerun", "track": "repe",  "bot_protected": True},
    {"firm": "Brookfield Asset Mgmt", "url": "https://brookfield.com/careers",                           "tier": "homerun", "track": "repe",  "bot_protected": False},
    {"firm": "Goldman Sachs",         "url": "https://www.goldmansachs.com/careers/search.html",         "tier": "homerun", "track": "ib",    "bot_protected": True},
    {"firm": "Morgan Stanley",        "url": "https://www.morganstanley.com/people-opportunities/search","tier": "homerun", "track": "ib",    "bot_protected": True},
    # Ashby job boards (JS-rendered) — confirmed live
    {"firm": "Stonepeak",             "url": "https://jobs.ashbyhq.com/stonepeak",            "tier": "homerun", "track": "infra", "bot_protected": False},
    {"firm": "Pretium Partners",      "url": "https://jobs.ashbyhq.com/pretium",              "tier": "reach",   "track": "repe",  "bot_protected": False},
    {"firm": "Bridge Investment Group","url": "https://jobs.ashbyhq.com/bridge-investment-group","tier": "target","track": "repe",  "bot_protected": False},
    # Homerun — Workday slugs unresolved; scraped via Playwright instead
    {"firm": "KKR Real Estate",       "url": "https://www.kkr.com/careers/career-opportunities",          "tier": "homerun", "track": "repe",  "bot_protected": False},
    {"firm": "Carlyle Group",         "url": "https://www.carlyle.com/careers",                           "tier": "homerun", "track": "repe",  "bot_protected": False},
    # Target — non-Workday or unresolved ATS
    # W.P. Carey is handled by jobvite.py — no duplicate here
    {"firm": "Digital Realty Trust",  "url": "https://hdep.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX", "tier": "target", "track": "repe", "bot_protected": False},
    {"firm": "BentallGreenOak",       "url": "https://www.bentallgreenoak.com/about-us/careers/",         "tier": "target",  "track": "repe",  "bot_protected": False},
    # Hines iCIMS requires auth — scrape careers page directly
    {"firm": "Hines",                 "url": "https://www.hines.com/careers",                             "tier": "target",  "track": "repe",  "bot_protected": False},
    # Safety — Workday slugs unresolved
    {"firm": "CBRE Capital Markets",  "url": "https://careers.cbre.com/en_US/careers/SearchJobs/",        "tier": "safety",  "track": "cm",    "bot_protected": False},
    {"firm": "Wells Fargo RE",        "url": "https://www.wellsfargojobs.com/en/",                        "tier": "safety",  "track": "ib",    "bot_protected": False},
    {"firm": "UBS Wealth Management", "url": "https://www.ubs.com/global/en/careers/professional-careers.html", "tier": "safety", "track": "ib", "bot_protected": False},
    {"firm": "State Street (SSGA)",   "url": "https://careers.statestreet.com/jobs/en-US/search",         "tier": "safety",  "track": "repe",  "bot_protected": False},
    # Jefferies — Oracle HCM
    {"firm": "Jefferies",             "url": "https://hdid.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs", "tier": "target", "track": "ib", "bot_protected": False},
    # Reach tier
    {"firm": "Starwood Capital",      "url": "https://www.starwoodcapital.com/about/careers",             "tier": "reach",   "track": "repe",  "bot_protected": False},
    {"firm": "Cerberus Capital",      "url": "https://www.cerberuscapital.com/careers",                   "tier": "reach",   "track": "repe",  "bot_protected": False},
    {"firm": "EQT / Exeter RE",       "url": "https://careers.eqtgroup.com",                             "tier": "reach",   "track": "repe",  "bot_protected": False},
    {"firm": "Tishman Speyer",        "url": "https://www.tishmanspeyer.com/about/careers",               "tier": "reach",   "track": "repe",  "bot_protected": False},
    {"firm": "Rockpoint Group",       "url": "https://www.rockpointgroup.com/careers",                   "tier": "reach",   "track": "repe",  "bot_protected": False},
    {"firm": "Dune Real Estate",      "url": "https://www.dunerep.com",                                  "tier": "reach",   "track": "repe",  "bot_protected": False},
    {"firm": "Harrison Street RE",    "url": "https://www.harrisonst.com/careers",                       "tier": "reach",   "track": "repe",  "bot_protected": False},
    {"firm": "Eastdil Secured",       "url": "https://www.eastdilsecured.com/careers",                   "tier": "reach",   "track": "cm",    "bot_protected": False},
    # Target tier
    {"firm": "I Squared Capital",     "url": "https://isquaredcapital.com/careers",                      "tier": "target",  "track": "infra", "bot_protected": False},
    {"firm": "AEW Capital Mgmt",      "url": "https://www.aew.com/about/careers",                        "tier": "target",  "track": "repe",  "bot_protected": False},
    {"firm": "Clarion Partners",      "url": "https://www.clarionpartners.com/about-us/careers",          "tier": "target",  "track": "repe",  "bot_protected": False},
    {"firm": "Heitman",               "url": "https://www.heitman.com/careers",                          "tier": "target",  "track": "repe",  "bot_protected": False},
    {"firm": "Walton Street Capital", "url": "https://www.waltonst.com",                                  "tier": "target",  "track": "repe",  "bot_protected": False},
    {"firm": "TA Realty",             "url": "https://www.tarealty.com/careers",                          "tier": "target",  "track": "repe",  "bot_protected": False},
    {"firm": "Somera Road",           "url": "https://someraroadinc.com",                                 "tier": "target",  "track": "repe",  "bot_protected": False},
    # Safety tier
    {"firm": "Marcus & Millichap",    "url": "https://www.marcusmillichap.com/careers",                  "tier": "safety",  "track": "cm",    "bot_protected": False},
    {"firm": "Stifel Financial",      "url": "https://www.stifel.com/careers",                           "tier": "safety",  "track": "ib",    "bot_protected": False},
    {"firm": "Revantage (Blackstone)","url": "https://www.revantage.com/careers",                        "tier": "safety",  "track": "repe",  "bot_protected": False},
    {"firm": "Fidelity Investments",  "url": "https://jobs.fidelity.com",                                "tier": "safety",  "track": "repe",  "bot_protected": False},
]



async def _scrape_one(context, firm: dict, log_fn) -> list[dict]:
    # Use a fresh page per firm to prevent navigation bleed-over between sites
    page = await context.new_page()
    jobs = []
    try:
        await page.goto(firm["url"], wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)
        html  = await page.content()
        soup  = BeautifulSoup(html, "lxml")
        today = datetime.utcnow().strftime("%Y-%m-%d")

        seen_titles = set()
        for a_tag in soup.find_all("a"):
            text = a_tag.get_text(strip=True)
            href = a_tag.get("href", "")
            if not text or text in seen_titles:
                continue
            if not is_match(text, check_noise=True):
                continue
            # Skip if href looks like a social/share link
            if any(s in href.lower() for s in ["twitter.com", "linkedin.com", "facebook.com", "mailto:", "javascript:"]):
                continue
            seen_titles.add(text)
            full_url = href if href.startswith("http") else firm["url"].rstrip("/") + "/" + href.lstrip("/")
            # Build a stable ID from the href path, falling back to title slug
            path_part = href.rstrip("/").split("/")[-1][:50] if href else ""
            id_part   = path_part if path_part else text.lower().replace(" ", "-")[:50]
            jobs.append({
                "id":          f"pw-{firm['firm'].lower().replace(' ', '-')[:18]}-{id_part}",
                "firm":        firm["firm"],
                "tier":        firm["tier"],
                "track":       firm["track"],
                "title":       text,
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
        log_fn(f"[playwright] {firm['firm']}: {len(jobs)} match(es)")
    except Exception as e:
        if firm.get("bot_protected"):
            log_fn(f"[playwright] {firm['firm']}: blocked/error (bot protection expected) — {e}")
        else:
            log_fn(f"[playwright] ERROR {firm['firm']}: {e}")
    finally:
        await page.close()
    return jobs


async def _run_all(log_fn) -> list[dict]:
    all_jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
        for firm in FIRMS:
            results = await _scrape_one(context, firm, log_fn)
            all_jobs.extend(results)
        await browser.close()
    return all_jobs


def scrape_all(log_fn=print) -> list[dict]:
    if not PLAYWRIGHT_AVAILABLE:
        log_fn("[playwright] Playwright not installed — skipping custom sites")
        return []
    return asyncio.run(_run_all(log_fn))
