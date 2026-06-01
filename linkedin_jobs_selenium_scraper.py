"""
Scrape LinkedIn jobs using `linkedin-jobs-scraper` (Selenium/Chrome), then find
HR/careers/contact emails for the company and export to Excel.

Why this script exists:
  - Your existing `linkedin_devops_jobs.py` finds LinkedIn job URLs via web search.
  - This script uses a real browser (Selenium) via `linkedin-jobs-scraper`.

Requirements:
  - `pip install -r requirements.txt`
  - Chrome/Chromium installed
  - Chromedriver matching your Chrome version in PATH

Authenticated mode (sometimes required):
  - Set env var `LI_AT_COOKIE` to your LinkedIn `li_at` cookie value.
    (See `linkedin-jobs-scraper` PyPI page: "Anonymous vs authenticated session")

Usage:
  python linkedin_jobs_selenium_scraper.py --query "DevOps Engineer" --location "India" --limit 50
  python linkedin_jobs_selenium_scraper.py --query "AWS DevOps Engineer" --location "Bangalore" --limit 30 --headless 0
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from job_hunter.company_lookup import find_emails_for_company


@dataclass
class Row:
    company: str
    email: str
    role: str
    linkedin_job_url: str = ""
    location: str = ""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LinkedIn job scraping (Selenium) + HR email lookup → Excel"
    )
    parser.add_argument("--query", required=True, help="LinkedIn keywords (e.g. 'DevOps Engineer')")
    parser.add_argument(
        "--location",
        default="India",
        help="LinkedIn location text (e.g. 'India', 'Bangalore')",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=40,
        metavar="N",
        help="Max jobs to scrape from LinkedIn (default: 40)",
    )
    parser.add_argument(
        "--max-companies",
        type=int,
        default=40,
        metavar="N",
        help="Max unique companies to look up emails for (default: 40)",
    )
    parser.add_argument(
        "--emails-per-company",
        type=int,
        default=3,
        metavar="N",
        help="Max emails to store per company (default: 3)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Seconds between company email lookups (default: 1.5)",
    )
    parser.add_argument(
        "--headless",
        type=int,
        default=1,
        help="1=headless (default), 0=show browser window",
    )
    parser.add_argument(
        "--slow-mo",
        type=float,
        default=0.5,
        help="Selenium slow motion seconds to reduce 429s (default: 0.5)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("Company_email.xlsx"),
        help="Output Excel file (default: Company_email.xlsx)",
    )
    args = parser.parse_args()

    # Import here so users who don't run this script aren't forced to have Chrome set up.
    from linkedin_jobs_scraper import LinkedinScraper
    from linkedin_jobs_scraper.events import Events, EventData
    from linkedin_jobs_scraper.query import Query, QueryOptions

    jobs: list[EventData] = []

    def on_data(data: EventData) -> None:
        if not data.company:
            return
        jobs.append(data)
        if len(jobs) % 10 == 0:
            print(f"Scraped {len(jobs)} job(s)...")

    def on_error(err: Exception) -> None:
        print(f"[SCRAPER_ERROR] {err}")

    scraper = LinkedinScraper(
        headless=bool(args.headless),
        max_workers=1,
        slow_mo=args.slow_mo,
        page_load_timeout=40,
    )
    scraper.on(Events.DATA, on_data)
    scraper.on(Events.ERROR, on_error)

    queries = [
        Query(
            query=args.query,
            options=QueryOptions(
                locations=[args.location],
                limit=int(args.limit),
            ),
        )
    ]

    print("Starting LinkedIn scrape...")
    print("If it fails in anonymous mode, set env var LI_AT_COOKIE (LinkedIn li_at cookie).")
    scraper.run(queries)
    print(f"Scrape complete: {len(jobs)} job(s).")

    # Unique companies (keep first job for role/url/location)
    by_company: dict[str, EventData] = {}
    for j in jobs:
        key = (j.company or "").strip().lower()
        if not key:
            continue
        if key not in by_company:
            by_company[key] = j
        if len(by_company) >= args.max_companies:
            break

    rows: list[Row] = []
    companies = list(by_company.values())
    print(f"Looking up emails for {len(companies)} unique company(ies)...\n")

    for i, j in enumerate(companies, start=1):
        company = (j.company or "").strip()
        title = (j.title or "").strip()
        link = (j.link or "").strip()
        place = (j.place or "").strip()

        print(f"[{i}/{len(companies)}] {company} — {title[:60]}")
        emails, _source = find_emails_for_company(
            company, website="", max_emails=int(args.emails_per_company)
        )
        if emails:
            email_cell = ", ".join(emails)
            print(f"    -> {email_cell}")
        else:
            email_cell = "NO email id"
            print("    -> no email found")

        rows.append(
            Row(
                company=company,
                email=email_cell,
                role=title or args.query,
                linkedin_job_url=link,
                location=place or args.location,
            )
        )

        # Save incrementally so you can stop anytime
        out_df = pd.DataFrame(
            {
                "Company Name": [r.company for r in rows],
                "Email ID": [r.email for r in rows],
                "Role": [r.role for r in rows],
                "LinkedIn Job URL": [r.linkedin_job_url for r in rows],
                "Location": [r.location for r in rows],
            }
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        out_df.to_excel(args.output, index=False)

        if args.delay > 0 and i < len(companies):
            time.sleep(args.delay)

    with_email = sum(1 for r in rows if r.email and "no email" not in r.email.lower())
    print(f"\nWrote {len(rows)} row(s) to {args.output.resolve()}")
    print(f"Rows with at least one email: {with_email}/{len(rows)}")


if __name__ == "__main__":
    main()

