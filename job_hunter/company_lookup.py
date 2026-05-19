"""Find HR / careers / contact emails for a company name via web search and scraping."""

from __future__ import annotations

import time
from urllib.parse import urlparse

from job_hunter.emails import (
    discover_career_links,
    extract_emails_from_text,
    extract_emails_from_url,
    fetch_page_text,
)
from job_hunter.search import search_career_pages, search_hr_emails_google


def _merge_unique(target: list[str], new: list[str]) -> None:
    seen = {e.lower() for e in target}
    for e in new:
        if e.lower() not in seen:
            seen.add(e.lower())
            target.append(e)


def find_emails_for_company(
    company: str,
    website: str = "",
    max_emails: int = 3,
    scrape_delay: float = 0.4,
) -> tuple[list[str], str]:
    """
    Return (emails, career_or_website_url) for a company.

  Uses optional website, Google snippets, career-page search, and linked pages.
    """
    company = company.strip()
    if not company:
        return [], ""

    emails: list[str] = []
    career_url = ""

    site = website.strip()
    if site and not site.startswith("http"):
        site = f"https://{site.lstrip('/')}"

    if site.startswith("http"):
        html, err = fetch_page_text(site)
        if not err:
            career_url = site
            _merge_unique(emails, extract_emails_from_text(html))
            for link in discover_career_links(site, html):
                _merge_unique(emails, extract_emails_from_url(link))
                if len(emails) >= max_emails:
                    break
                if scrape_delay > 0:
                    time.sleep(scrape_delay)
        else:
            _merge_unique(emails, extract_emails_from_url(site))

    _merge_unique(emails, search_hr_emails_google(company, max_results=8))

    urls = search_career_pages(company, max_results=6)
    for url in urls:
        if not career_url:
            career_url = url
        _merge_unique(emails, extract_emails_from_url(url))
        if len(emails) >= max_emails:
            break
        if scrape_delay > 0:
            time.sleep(scrape_delay)

    if not career_url and urls:
        career_url = urls[0]
    elif not career_url and site:
        career_url = site

    if not career_url and emails:
        netloc = urlparse(emails[0].split("@", 1)[-1]).netloc
        if netloc:
            career_url = f"https://{netloc}"

    return emails[:max_emails], career_url
