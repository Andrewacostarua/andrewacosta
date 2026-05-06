"""Main orchestrator — runs all scrapers, detects new jobs, writes jobs.json, sends alerts."""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from scrapers import greenhouse, workday, lever, smartrecruiters, icims, jobvite, playwright_scraper
from notifier import send_alert

# All 50 target firms — used to generate "not open yet" entries in jobs.json
MASTER_FIRMS = [
    # Homerun
    {"name": "Blackstone (BREP)",      "tier": "homerun", "track": "repe", "careers_url": "https://careers.smartrecruiters.com/Blackstone"},
    {"name": "KKR Real Estate",         "tier": "homerun", "track": "repe", "careers_url": "https://www.kkr.com/careers/career-opportunities"},
    {"name": "Apollo Global Management","tier": "homerun", "track": "repe", "careers_url": "https://boards.greenhouse.io/apollo"},
    {"name": "Carlyle Group",           "tier": "homerun", "track": "repe", "careers_url": "https://www.carlyle.com/careers"},
    {"name": "Brookfield Asset Mgmt",   "tier": "homerun", "track": "repe", "careers_url": "https://brookfield.com/careers"},
    {"name": "Goldman Sachs",           "tier": "homerun", "track": "ib",   "careers_url": "https://www.goldmansachs.com/careers/search.html"},
    {"name": "Morgan Stanley",          "tier": "homerun", "track": "ib",   "careers_url": "https://www.morganstanley.com/people-opportunities/search"},
    {"name": "Stonepeak",               "tier": "homerun", "track": "infra","careers_url": "https://jobs.ashbyhq.com/stonepeak"},
    {"name": "BlackRock Real Assets",   "tier": "homerun", "track": "repe", "careers_url": "https://blackrock.wd1.myworkdayjobs.com/BlackRock_Professional"},
    # Reach
    {"name": "Ares Management",         "tier": "reach",   "track": "repe", "careers_url": "https://careers.smartrecruiters.com/Ares"},
    {"name": "Starwood Capital",        "tier": "reach",   "track": "repe", "careers_url": "https://www.starwoodcapital.com/about/careers"},
    {"name": "TPG Real Estate",         "tier": "reach",   "track": "repe", "careers_url": "https://boards.greenhouse.io/tpgcareers"},
    {"name": "Cerberus Capital",        "tier": "reach",   "track": "repe", "careers_url": "https://www.cerberuscapital.com/careers"},
    {"name": "EQT / Exeter RE",         "tier": "reach",   "track": "repe", "careers_url": "https://careers.eqtgroup.com"},
    {"name": "Tishman Speyer",          "tier": "reach",   "track": "repe", "careers_url": "https://www.tishmanspeyer.com/about/careers"},
    {"name": "Related Companies",       "tier": "reach",   "track": "repe", "careers_url": "https://www.related.jobs/"},
    {"name": "Rockpoint Group",         "tier": "reach",   "track": "repe", "careers_url": "https://www.rockpointgroup.com/careers"},
    {"name": "Pretium Partners",        "tier": "reach",   "track": "repe", "careers_url": "https://jobs.ashbyhq.com/pretium"},
    {"name": "Dune Real Estate",        "tier": "reach",   "track": "repe", "careers_url": "https://www.dunerep.com"},
    {"name": "Harrison Street RE",      "tier": "reach",   "track": "repe", "careers_url": "https://www.harrisonst.com/careers"},
    {"name": "Eastdil Secured",         "tier": "reach",   "track": "cm",   "careers_url": "https://www.eastdilsecured.com/careers"},
    # Target
    {"name": "Blue Owl Capital",        "tier": "target",  "track": "repe", "careers_url": "https://blueowl.wd1.myworkdayjobs.com/blueowl"},
    {"name": "W. P. Carey",             "tier": "target",  "track": "repe", "careers_url": "https://jobs.jobvite.com/wpccareers"},
    {"name": "Digital Realty Trust",    "tier": "target",  "track": "repe", "careers_url": "https://careers.digitalrealty.com/"},
    {"name": "I Squared Capital",       "tier": "target",  "track": "infra","careers_url": "https://isquaredcapital.com/careers"},
    {"name": "AEW Capital Mgmt",        "tier": "target",  "track": "repe", "careers_url": "https://www.aew.com/about/careers"},
    {"name": "LaSalle Investment",      "tier": "target",  "track": "repe", "careers_url": "https://jll.wd1.myworkdayjobs.com/lasallecareers"},
    {"name": "BentallGreenOak",         "tier": "target",  "track": "repe", "careers_url": "https://www.bentallgreenoak.com/about-us/careers/"},
    {"name": "Clarion Partners",        "tier": "target",  "track": "repe", "careers_url": "https://www.clarionpartners.com/about-us/careers"},
    {"name": "Hines",                   "tier": "target",  "track": "repe", "careers_url": "https://www.hines.com/careers"},
    {"name": "Nuveen Real Estate",      "tier": "target",  "track": "repe", "careers_url": "https://tiaa.wd1.myworkdayjobs.com/Search"},
    {"name": "Bridge Investment Group", "tier": "target",  "track": "repe", "careers_url": "https://jobs.ashbyhq.com/bridge-investment-group"},
    {"name": "Heitman",                 "tier": "target",  "track": "repe", "careers_url": "https://www.heitman.com/careers"},
    {"name": "Walton Street Capital",   "tier": "target",  "track": "repe", "careers_url": "https://www.waltonst.com"},
    {"name": "TA Realty",               "tier": "target",  "track": "repe", "careers_url": "https://www.tarealty.com/careers"},
    {"name": "Somera Road",             "tier": "target",  "track": "repe", "careers_url": "https://someraroadinc.com"},
    {"name": "Jefferies",               "tier": "target",  "track": "ib",   "careers_url": "https://www.jefferies.com/careers/"},
    # Safety
    {"name": "JLL Capital Markets",     "tier": "safety",  "track": "cm",   "careers_url": "https://jll.wd1.myworkdayjobs.com/jllcareers"},
    {"name": "CBRE Capital Markets",    "tier": "safety",  "track": "cm",   "careers_url": "https://careers.cbre.com/en_US/careers/SearchJobs/"},
    {"name": "Cushman & Wakefield",     "tier": "safety",  "track": "cm",   "careers_url": "https://cw.wd1.myworkdayjobs.com/External"},
    {"name": "Walker & Dunlop",         "tier": "safety",  "track": "cm",   "careers_url": "https://walkerdunlop.wd1.myworkdayjobs.com/WD"},
    {"name": "Marcus & Millichap",      "tier": "safety",  "track": "cm",   "careers_url": "https://www.marcusmillichap.com/careers"},
    {"name": "Wells Fargo RE",          "tier": "safety",  "track": "ib",   "careers_url": "https://www.wellsfargojobs.com/en/"},
    {"name": "KeyBank RE",              "tier": "safety",  "track": "cm",   "careers_url": "https://keybank.wd5.myworkdayjobs.com/External_Career_Site"},
    {"name": "UBS Wealth Management",   "tier": "safety",  "track": "ib",   "careers_url": "https://www.ubs.com/global/en/careers/professional-careers.html"},
    {"name": "Stifel Financial",        "tier": "safety",  "track": "ib",   "careers_url": "https://www.stifel.com/careers"},
    {"name": "Revantage (Blackstone)",  "tier": "safety",  "track": "repe", "careers_url": "https://www.revantage.com/careers"},
    {"name": "Fidelity Investments",    "tier": "safety",  "track": "repe", "careers_url": "https://jobs.fidelity.com"},
    {"name": "State Street (SSGA)",     "tier": "safety",  "track": "repe", "careers_url": "https://careers.statestreet.com/jobs/en-US/search"},
    {"name": "Berkadia",                "tier": "safety",  "track": "cm",   "careers_url": "https://boards.greenhouse.io/berkadia"},
]

ROOT        = Path(__file__).parent
JOBS_FILE   = ROOT / "jobs.json"
KNOWN_FILE  = ROOT / "known_ids.json"
LOG_FILE    = ROOT / "scrape_log.txt"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="a"),
    ],
)
log = logging.getLogger(__name__)


def load_known_ids() -> set[str]:
    if KNOWN_FILE.exists():
        return set(json.loads(KNOWN_FILE.read_text()))
    return set()


def save_known_ids(ids: set[str]) -> None:
    KNOWN_FILE.write_text(json.dumps(sorted(ids), indent=2))


def load_existing_jobs() -> list[dict]:
    if JOBS_FILE.exists():
        data = json.loads(JOBS_FILE.read_text())
        return data.get("jobs", [])
    return []


def build_firms_status(all_jobs: list[dict]) -> list[dict]:
    """Cross-reference scraped jobs against MASTER_FIRMS; tag each firm with open_count."""
    counts: dict[str, int] = {}
    for job in all_jobs:
        counts[job["firm"]] = counts.get(job["firm"], 0) + 1
    firms_status = []
    for f in MASTER_FIRMS:
        firms_status.append({
            "name":        f["name"],
            "tier":        f["tier"],
            "track":       f["track"],
            "careers_url": f["careers_url"],
            "open_count":  counts.get(f["name"], 0),
        })
    return firms_status


def write_jobs(all_jobs: list[dict]) -> None:
    output = {
        "last_run":    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "total_found": len(all_jobs),
        "firms":       build_firms_status(all_jobs),
        "jobs":        all_jobs,
    }
    JOBS_FILE.write_text(json.dumps(output, indent=2))


def mark_new_jobs(all_jobs: list[dict], known_ids: set[str]) -> list[dict]:
    """Set is_new=True on jobs not in known_ids; return list of newly found jobs."""
    new_jobs = []
    for job in all_jobs:
        if job["id"] not in known_ids:
            job["is_new"] = True
            new_jobs.append(job)
        else:
            job["is_new"] = False
    return new_jobs


def deduplicate(jobs: list[dict]) -> list[dict]:
    seen = set()
    out  = []
    for job in jobs:
        if job["id"] not in seen:
            seen.add(job["id"])
            out.append(job)
    return out


def main():
    log.info("=== Scraper run started ===")
    run_start = datetime.now(timezone.utc)

    known_ids = load_known_ids()
    log.info(f"Known IDs loaded: {len(known_ids)}")

    all_jobs: list[dict] = []

    # --- Greenhouse ---
    log.info("Running Greenhouse scrapers...")
    all_jobs.extend(greenhouse.scrape_all(log_fn=log.info))

    # --- Workday ---
    log.info("Running Workday scrapers...")
    all_jobs.extend(workday.scrape_all(log_fn=log.info))

    # --- Lever ---
    log.info("Running Lever scrapers...")
    all_jobs.extend(lever.scrape_all(log_fn=log.info))

    # --- Jobvite ---
    log.info("Running Jobvite scrapers...")
    all_jobs.extend(jobvite.scrape_all(log_fn=log.info))

    # --- SmartRecruiters ---
    log.info("Running SmartRecruiters scrapers...")
    all_jobs.extend(smartrecruiters.scrape_all(log_fn=log.info))

    # --- iCIMS ---
    log.info("Running iCIMS scrapers...")
    all_jobs.extend(icims.scrape_all(log_fn=log.info))

    # --- Playwright (custom sites + Ashby) ---
    log.info("Running Playwright scrapers...")
    all_jobs.extend(playwright_scraper.scrape_all(log_fn=log.info))

    all_jobs = deduplicate(all_jobs)
    log.info(f"Total matches after dedup: {len(all_jobs)}")

    # Detect new jobs and mark them
    new_jobs = mark_new_jobs(all_jobs, known_ids)
    log.info(f"New jobs this run: {len(new_jobs)}")

    # Update known_ids
    for job in all_jobs:
        known_ids.add(job["id"])
    save_known_ids(known_ids)

    # Write jobs.json
    write_jobs(all_jobs)
    log.info("jobs.json written")

    # Send email alert
    if new_jobs:
        send_alert(new_jobs)
    else:
        log.info("No new jobs — no email sent")

    elapsed = (datetime.now(timezone.utc) - run_start).seconds
    log.info(f"=== Run complete in {elapsed}s — {len(all_jobs)} total, {len(new_jobs)} new ===")


if __name__ == "__main__":
    main()
