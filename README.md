# Analyst Job Tracker

Scrapes ~50 finance firm career pages daily for 2027 FT analyst roles across REPE, IB, Infrastructure PE, and Capital Markets. Sends Gmail alerts on new postings and serves a live dashboard via GitHub Pages — no backend, no server, just GitHub Actions committing `jobs.json` to the repo.

---

## How it works

```
GitHub Actions (8am ET Mon–Fri)
  → scraper.py
      → scrapers/greenhouse.py   (Apollo, TPG, Berkadia)
      → scrapers/workday.py      (BlackRock, Blue Owl, JLL, LaSalle, Nuveen, CW, KeyBank, Walker & Dunlop)
      → scrapers/smartrecruiters.py  (Ares)
      → scrapers/icims.py        (Related Companies)
      → scrapers/jobvite.py      (W.P. Carey)
      → scrapers/playwright_scraper.py  (all JS-heavy / custom sites)
  → jobs.json + known_ids.json committed to repo
  → notifier.py sends Gmail alert if new roles found
  → GitHub Pages serves index.html (reads jobs.json dynamically)
```

---

## One-time setup

### 1. Fork / create the repo on GitHub

Push this folder to a new GitHub repo. The name doesn't matter.

### 2. Enable GitHub Pages

1. Go to **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / `(root)`
4. Save — your dashboard will be live at `https://<your-username>.github.io/<repo-name>/`

### 3. Add Gmail credentials as Secrets

The scraper emails you when new roles are found. You need a Gmail App Password (not your regular password).

**Create an App Password:**
1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Select app: **Mail**, device: **Other** → name it "job-tracker"
3. Copy the 16-character password

**Add to GitHub Secrets:**
1. Go to **Settings → Secrets and variables → Actions**
2. Add two secrets:
   - `GMAIL_ADDRESS` — your full Gmail address (e.g. `andrew@gmail.com`)
   - `GMAIL_APP_PASSWORD` — the 16-character app password

### 4. Run the scraper manually once

Go to **Actions → Daily Job Scraper → Run workflow** to trigger the first run immediately. It will:
- Scrape all 50 firms
- Commit `jobs.json` and `known_ids.json` to the repo
- Send an email with any roles found

After that it runs automatically at 8am ET every weekday.

---

## Dashboard features

- **Grouped by firm** — one card per firm, all open roles listed inside
- **Tier filter** — Homerun / Reach / Target / Safety
- **Search** — filter by firm name or role title
- **NEW badge** — roles first seen in the last 7 days
- **Not Open Yet** — dashed placeholder cards for firms with no current openings, with a direct link to their careers page
- **Dismiss** — click ✕ on any role to hide it permanently; the firm stays visible as "Not Open Yet" until a new role appears
- **Application Tracker** — set status (Applied / Phone Screen / Superday / Offer / Rejected), deadline, and notes per role; saved to your browser
- **Expiring Soon banner** — appears above the grid when any role has a deadline within 14 days
- **Charts** — pipeline doughnut and tier breakdown bar chart

---

## Firm coverage (50 firms)

| Tier | Firms |
|------|-------|
| Homerun | Blackstone, KKR, Apollo, Carlyle, Brookfield, Goldman Sachs, Morgan Stanley, Stonepeak, BlackRock |
| Reach | Ares, Starwood, TPG, Cerberus, EQT/Exeter, Tishman Speyer, Related, Rockpoint, Pretium, Dune, Harrison Street, Eastdil |
| Target | Blue Owl, W.P. Carey, Digital Realty, I Squared, AEW, LaSalle, BentallGreenOak, Clarion, Hines, Nuveen, Bridge, Heitman, Walton Street, TA Realty, Somera Road, Jefferies |
| Safety | JLL, CBRE, Cushman & Wakefield, Walker & Dunlop, Marcus & Millichap, Wells Fargo, KeyBank, UBS, Stifel, Revantage, Fidelity, State Street, Berkadia |

---

## Match criteria

A role is included if:
- Title contains **analyst** or **associate**
- Title also contains a domain qualifier: `real estate`, `investment banking`, `capital markets`, `acquisitions`, `private equity`, `infrastructure`, `financial`, `credit`, `underwriting`, `transaction`, `equity`, `debt`, `fund`, `multifamily`, etc.
- Title does **not** contain: `senior`, `vice president`, `director`, `managing director`, `principal`, `technology analyst`, `data analyst`, `compliance analyst`, `legal analyst`, `business analyst`, etc.

---

## Adding a firm

1. Identify which ATS they use (check their careers URL — Workday, Greenhouse, Lever, etc.)
2. Add an entry to the right scraper in `scrapers/`
3. Add the firm to `MASTER_FIRMS` in `scraper.py` so it appears as "Not Open Yet" when no roles are open

---

## Local development

```bash
pip install -r requirements.txt
playwright install chromium

# Run scraper (generates jobs.json)
python scraper.py

# Serve dashboard locally
python -m http.server 8000
# → open http://localhost:8000
```

> Goldman Sachs, Morgan Stanley, and Blackstone use Cloudflare bot protection — Playwright will be blocked for those three. Check their pages manually when the scraper reports 0 results.
