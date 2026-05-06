# Analyst Job Tracker — Claude Code Context

## Project Goal
Scrape ~50 finance firm career pages daily, detect 2027 FT analyst roles, send email alerts, serve a dashboard on GitHub Pages. No backend — everything runs via GitHub Actions committing to the repo.

## User Background
- Andrew (andrew@acostarua.com), SMU rising senior, Economics + Stats, May 2027 grad
- Interning at Blue Owl Capital (Chicago) summer 2026
- Targeting REPE, IB, Infrastructure PE, and adjacent 2027 FT analyst roles
- Knows Python/R — zero web dev background; explain non-obvious steps

## Architecture
```
scraper.py → jobs.json → index.html (GitHub Pages)
                       → email (Gmail SMTP on new jobs)
GitHub Actions runs scraper daily at 8am ET (noon UTC)
```

## Key Files
| File | Purpose |
|------|---------|
| `scraper.py` | Main orchestrator — calls all scraper modules |
| `scrapers/greenhouse.py` | Greenhouse ATS (public JSON API, no auth) |
| `scrapers/workday.py` | Workday ATS (POST to internal search API) |
| `scrapers/lever.py` | Lever ATS |
| `scrapers/playwright_scraper.py` | Headless Chromium for JS-heavy/custom sites |
| `notifier.py` | Gmail SMTP email alerts |
| `jobs.json` | Output — committed after each scraper run |
| `known_ids.json` | Tracks seen job IDs to detect new ones |
| `index.html` | Dashboard (vanilla JS, fetches jobs.json) |
| `.github/workflows/scrape.yml` | GitHub Actions cron |

## Scraper Match Criteria
Include if ALL true:
1. Title contains: `analyst` OR `associate` (only if paired with "real estate" or "infrastructure")
2. Title does NOT contain: `senior`, `vice president`, `vp`, `director`, `managing director`, `md`, `principal`
3. Ideally contains: `real estate`, `infrastructure`, `net lease`, `digital`, `acquisitions`, `capital markets`, `investment banking`

## Firm Tiers (50 firms total)
- **Homerun (9)**: Blackstone, KKR, Apollo, Carlyle, Brookfield, Goldman, Morgan Stanley, Stonepeak, BlackRock
- **Reach (12)**: Ares, Starwood, TPG, Cerberus, EQT/Exeter, Tishman Speyer, Related, Rockpoint, Pretium, Dune, Harrison Street, Eastdil
- **Target (16)**: Blue Owl, W.P. Carey, Digital Realty, I Squared, AEW, LaSalle, BentallGreenOak, Clarion, Hines, Nuveen, Bridge, Heitman, Walton Street, TA Realty, Somera Road, Jefferies
- **Safety (13)**: JLL, CBRE, Cushman, Walker & Dunlop, Marcus & Millichap, Wells Fargo, KeyBank, UBS, Stifel, Revantage, Fidelity, State Street, Berkadia

## ATS Modules
- **Greenhouse**: Apollo, Stonepeak, Ares, TPG, Related, Pretium, Blue Owl, Bridge — `https://boards-api.greenhouse.io/v1/boards/{slug}/jobs`
- **Workday**: KKR, Carlyle, BlackRock, W.P. Carey, Digital Realty, LaSalle, BentallGreenOak, Nuveen, Jefferies, JLL, CBRE, Cushman, Wells Fargo, KeyBank, UBS, State Street — POST to `https://{subdomain}.wd1.myworkdayjobs.com/wday/cxs/{subdomain}/{jobsite}/jobs`
- **iCIMS**: Hines, Walker & Dunlop, Berkadia
- **Playwright/Custom**: Blackstone, Brookfield, Goldman, Morgan Stanley, Starwood, Cerberus, EQT, Tishman Speyer, Rockpoint, Dune, Harrison Street, Eastdil, I Squared, AEW, Clarion, Heitman, Walton Street, TA Realty, Somera Road, Marcus & Millichap, Stifel, Revantage, Fidelity

## Notifications
- To: andrew@acostarua.com
- Gmail SMTP with App Password (stored as GitHub Secrets: `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`)
- Subject: "🔔 {n} New Analyst Role(s) Found — {date}"
- HTML email with Firm, Title, Tier, Apply URL

## jobs.json Structure
```json
{
  "last_run": "ISO datetime",
  "total_found": 12,
  "jobs": [{
    "id": "unique-id", "firm": "Stonepeak", "tier": "homerun",
    "track": "infra", "title": "Analyst, Infrastructure",
    "url": "https://...", "location": "New York, NY",
    "posted_date": "2026-07-14", "first_seen": "2026-07-15",
    "is_new": true, "chance": 18,
    "salary": "$115–125k base", "bonus": "+$60–80k bonus", "hours": "70–80 hrs/wk"
  }]
}
```

## Dashboard (index.html)
- Dark navy header, white cards, tier-colored badges (gold/purple/blue/green)
- Fetches jobs.json dynamically (no hardcoded data)
- Filter buttons: All / Homerun / Reach / Target / Safety
- NEW badge (bright green) for jobs seen in last 7 days
- Status tracker table with localStorage persistence
- Chart.js: pipeline doughnut + tier odds bar chart

## Error Handling
- Each firm wrapped in try/except — one failure never kills the full run
- Log all errors to `scrape_log.txt` (committed after each run)
- Goldman, Morgan Stanley, Blackstone: Cloudflare bot protection — catch silently, mark as "manual check"

## Implementation Order
1. ✅ Create repo structure and all empty files
2. Build Greenhouse scraper — test vs Blue Owl + Stonepeak
3. Build Workday scraper — test vs KKR + JLL
4. Build jobs.json output with correct structure
5. Build email notifier — send test to andrew@acostarua.com
6. Build new-job detection (known_ids.json comparison)
7. Build index.html dashboard
8. Add Playwright scrapers (Goldman, MS, Blackstone, Brookfield)
9. Build GitHub Actions workflow
10. Write README with setup steps
