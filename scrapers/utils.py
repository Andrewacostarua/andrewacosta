"""Shared job-matching logic — single source of truth for all scrapers."""

EXCLUDE_TERMS = frozenset({
    # Seniority
    "senior", "vice president", "vp ", " vp", "director", "managing director",
    "md ", " md", "principal", "sr. ",
    # Clearly non-investment roles
    "technology analyst", "data analyst", "systems analyst", "it analyst",
    "compliance analyst", "legal analyst", "marketing analyst", "business analyst",
    "pmo analyst", "governance analyst", "lease abstraction", "lease analyst",
    "research analyst", "quality analyst", "data quality",
    "workforce", "procurement", "payoff", "boarding analyst",
    "information technology",
    # Program types not relevant to FT 2027 search
    "rotational", "trainee", "programme", "internship", "intern",
    "2025 ", "2026 ", "summer 2025", "summer 2026", "summer analyst",  # wrong cycle
    "class of 2025", "class of 2026",
    # Non-target function keywords
    "product marketing", "hud", "affordable housing", "special servicing",
    "loan servicing", "loan administration", "asset servicing",
    # Back-office / operations (not investment analysis)
    "fund accounting", "fund operations", "fund admin",
    "loan origination specialist", "asset administration",
})

# "analyst" or "associate" must be accompanied by at least one of these.
# Removed bare "financial" — too broad (catches Financial Systems Analyst, etc.)
RELEVANT_TERMS = frozenset({
    # Core investment / RE
    "real estate", "infrastructure", "investment banking",
    "capital markets", "acquisitions", "acquisition", "private equity",
    "asset management", "portfolio",
    # Finance instruments / activities
    "credit", "underwriting", "transaction", "valuation", "origination",
    "structured finance", "net lease", "debt", "equity",
    # Industry / product
    "investment", "fund", "securities", "multifamily", "commercial real estate",
    "financial analyst",  # explicit phrase, not bare "financial"
    # Investor-facing
    "investor relations",
    # IB / Wealth management
    "wealth management", "private wealth", "private banking", "private client",
})

# International location signals — any job with these in the location is excluded.
INTL_LOCATION_SIGNALS = frozenset({
    "philippines", "india", "australia", "germany", "france", "united kingdom",
    "london", "paris", "munich", "singapore", "japan", "canada", "toronto",
    "mexico", "brazil", "dubai", "uae", "bengaluru", "bangalore",
    "taguig", "manila", "budapest", "porto", "berlin", "hong kong", "tokyo",
    "sydney", "amsterdam", "zurich", "stockholm", "geneva", "milan",
    "madrid", "dublin", "warsaw", "prague", "johannesburg", "delhi",
    "mumbai", "beijing", "shanghai", "seoul", "taipei", "jakarta",
    " deu", " fra", " gbr", " ind", " aus", " sgp", " jpn", " chn",
    "apac", "emea", "asia pacific",
})

# US locations Andrew actually targets. Blank/remote always pass.
TARGET_US_LOCATIONS = frozenset({
    "new york", "new york city", "nyc", "manhattan", "brooklyn",
    "chicago",
    "san francisco", "sf", "palo alto", "menlo park",
    "los angeles",
    "boston",
    "dallas", "houston",
    "washington", "dc",
    "charlotte",
    "miami",
    "denver",
    "atlanta",
    "seattle",
    "philadelphia",
    "greenwich", "stamford", "westport", "darien", "new canaan", "norwalk", "fairfield",
    "westchester", "white plains", "purchase", "harrison", "rye",  # NY/CT commuter corridor
    "newport beach",
})

NOISE_PATTERNS = frozenset({
    "share", "twitter", "linkedin", "facebook", "email", "print",
    "apply now", "view all", "learn more", "sign in", "log in",
    "minutes ago", "days ago", "hours ago",
})


def is_match(title: str, *, check_noise: bool = False) -> bool:
    """Return True if title looks like a relevant analyst/associate role."""
    t = title.lower()

    if check_noise:
        if len(title) < 8 or len(title) > 120:
            return False
        if any(n in t for n in NOISE_PATTERNS):
            return False

    if any(ex in t for ex in EXCLUDE_TERMS):
        return False

    has_analyst   = "analyst" in t
    has_associate = "associate" in t
    if not (has_analyst or has_associate):
        return False

    # "associate" without "analyst" is typically post-MBA at finance firms.
    # Only pass if the title explicitly names real estate or infrastructure.
    if has_associate and not has_analyst:
        return "real estate" in t or "infrastructure" in t

    return any(rel in t for rel in RELEVANT_TERMS)


def is_target_location(location: str) -> bool:
    """Return True if location is a target US city (or unknown/remote).

    Unknown/blank locations pass — they may be remote or the scraper
    couldn't parse them. International signals always fail.
    """
    if not location or not location.strip():
        return True

    loc = location.lower()

    if any(sig in loc for sig in INTL_LOCATION_SIGNALS):
        return False

    # If it mentions a US state abbreviation or a target city, pass it.
    if any(city in loc for city in TARGET_US_LOCATIONS):
        return True

    # "united states" with no target city — still US, let scraper pass it,
    # dashboard will surface the location for manual review.
    if "united states" in loc or ", ny" in loc or ", il" in loc or ", tx" in loc or ", ca" in loc:
        return True

    # Unrecognized location — let it through rather than silently drop.
    return True
