from __future__ import annotations

import re

# 1-4 years, 2-3 yrs, 1 to 3 years experience, etc.
RANGE_PATTERN = re.compile(
    r"\b(\d{1,2})\s*[-–—to]+\s*(\d{1,2})\s*\+?\s*(years?|yrs?\.?|year\s+exp)\b",
    re.I,
)
SINGLE_YEAR_PATTERN = re.compile(
    r"\b(\d{1,2})\s*\+?\s*(years?|yrs?\.?|year\s+exp)\b",
    re.I,
)
# Obvious senior-only postings
SENIOR_EXCLUDE = re.compile(
    r"\b(10\+|15\+|20\+|[5-9]\s*\+\s*years|[5-9]\s*[-–]\s*\d+\s*years|"
    r"8\s*\+?\s*years|9\s*\+?\s*years|10\s*[-–]\s*\d+\s*years)\b",
    re.I,
)

ENTRY_KEYWORDS = re.compile(
    r"\b(junior|associate|entry[\s-]?level|early\s+career|1[\s-]?4\s+years?)\b",
    re.I,
)


def _years_in_range(n: int, min_y: int, max_y: int) -> bool:
    return min_y <= n <= max_y


def text_matches_experience(text: str, min_years: int, max_years: int) -> bool:
    """True if listing text suggests experience within [min_years, max_years]."""
    if not text:
        return True  # no signal — keep listing

    has_range = bool(RANGE_PATTERN.search(text))
    has_single = bool(SINGLE_YEAR_PATTERN.search(text))
    if not has_range and not has_single:
        if ENTRY_KEYWORDS.search(text):
            return True
        if SENIOR_EXCLUDE.search(text):
            return False
        return True  # ambiguous — include

    for m in RANGE_PATTERN.finditer(text):
        lo, hi = int(m.group(1)), int(m.group(2))
        if lo > hi:
            lo, hi = hi, lo
        if hi < min_years or lo > max_years:
            continue
        if lo <= max_years and hi >= min_years:
            return True
        if _years_in_range(lo, min_years, max_years) or _years_in_range(hi, min_years, max_years):
            return True

    for m in SINGLE_YEAR_PATTERN.finditer(text):
        n = int(m.group(1))
        if _years_in_range(n, min_years, max_years):
            return True
        if n > max_years:
            return False

    if SENIOR_EXCLUDE.search(text):
        return False

    return True


def experience_query_suffix(min_years: int, max_years: int) -> str:
    """Terms appended to search queries."""
    return f'"{min_years}-{max_years} years experience" OR "{min_years} to {max_years} years"'
