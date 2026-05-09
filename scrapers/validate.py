"""URL validator — strips dead job links before they hit the dashboard.

Runs after all scrapers complete. Checks every job URL in parallel with
HEAD requests. Any job returning 4xx is removed so the dashboard never
shows a link Andrew can't open. LinkedIn URLs are exempt — they redirect
to an archived view rather than 404, so they're always safe to keep.
"""

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}
_TIMEOUT  = 10
_WORKERS  = 12


def _is_alive(url: str) -> bool:
    """Return True if URL resolves to a non-4xx response."""
    if not url:
        return False
    # LinkedIn archives expired posts instead of 404ing — always valid
    if "linkedin.com" in url:
        return True
    try:
        r = requests.head(url, headers=_HEADERS, timeout=_TIMEOUT,
                          allow_redirects=True)
        if r.status_code == 405:
            # HEAD not allowed — try GET with a byte-range to keep it cheap
            r = requests.get(url, headers={**_HEADERS, "Range": "bytes=0-0"},
                             timeout=_TIMEOUT, allow_redirects=True)
        return r.status_code < 400
    except requests.RequestException:
        return False


def validate(jobs: list[dict], log_fn=print) -> list[dict]:
    """Return only jobs whose URLs are alive. Logs removed count."""
    if not jobs:
        return jobs

    results: dict[str, bool] = {}

    with ThreadPoolExecutor(max_workers=_WORKERS) as ex:
        future_to_id = {
            ex.submit(_is_alive, j["url"]): j["id"]
            for j in jobs
        }
        for future in as_completed(future_to_id):
            job_id = future_to_id[future]
            try:
                results[job_id] = future.result()
            except Exception:
                results[job_id] = False

    live    = [j for j in jobs if results.get(j["id"], False)]
    removed = len(jobs) - len(live)

    if removed:
        dead_firms = [j["firm"] for j in jobs if not results.get(j["id"], False)]
        log_fn(f"[validate] Removed {removed} dead link(s): {', '.join(dead_firms)}")
    else:
        log_fn(f"[validate] All {len(jobs)} links alive")

    return live
