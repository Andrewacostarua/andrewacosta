"""Shared job-matching logic — single source of truth for all scrapers."""

# Titles containing any of these are always excluded, regardless of other terms.
# Covers both seniority levels above analyst and clearly non-investment roles.
EXCLUDE_TERMS = frozenset({
    # Seniority
    "senior", "vice president", "vp ", " vp", "director", "managing director",
    "md ", " md", "principal", "sr. ",
    # Non-investment role patterns (substring match, so order matters for specificity)
    "technology analyst", "data analyst", "systems analyst", "it analyst",
    "compliance analyst", "legal analyst", "marketing analyst", "business analyst",
    "pmo analyst", "governance analyst", "lease abstraction",
    "workforce", "procurement", "payoff", "boarding analyst",
    "information technology",
})

# "analyst" or "associate" must be accompanied by at least one of these
# for the title to count as a relevant role.
RELEVANT_TERMS = frozenset({
    # Core investment / RE
    "real estate", "infrastructure", "investment banking", "investment",
    "capital markets", "acquisitions", "acquisition", "private equity",
    "asset management", "assets", "portfolio",
    # Finance instruments / activities
    "credit", "underwriting", "transaction", "valuation", "origination",
    "structured", "net lease", "debt", "equity",
    # Industry / product
    "banking", "fund", "securities", "multifamily", "commercial real estate",
    # Broad finance — kept because "Financial Analyst" at a REPE/IB firm is relevant
    "financial",
    # Investor-facing
    "investor relations",
})

# Noise patterns specific to Playwright scraping of raw HTML pages
# (share buttons, nav items, etc. that can look like job titles)
NOISE_PATTERNS = frozenset({
    "share", "twitter", "linkedin", "facebook", "email", "print",
    "apply now", "view all", "learn more", "sign in", "log in",
    "minutes ago", "days ago", "hours ago",
})


def is_match(title: str, *, check_noise: bool = False) -> bool:
    """Return True if title looks like a relevant analyst/associate role.

    check_noise: enable extra noise-pattern filter for Playwright (raw HTML) scrapers.
    """
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

    return any(rel in t for rel in RELEVANT_TERMS)
