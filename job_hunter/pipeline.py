from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from job_hunter.emails import extract_emails_from_url
from job_hunter.search import JobListing, SearchConfig, search_all_jobs, search_career_pages


@dataclass
class ContactRow:
    company: str
    email: str
    website: str
    job_title: str
    job_url: str
    career_page: str
    source: str
    location: str
    role_searched: str = ""
    experience_range: str = ""
    status: str = ""


@dataclass
class PipelineConfig:
    search: SearchConfig
    delay_seconds: float = 1.5
    max_companies: int = 40
    emails_per_company: int = 3


def find_emails_for_company(company: str, job: JobListing) -> tuple[list[str], str]:
    """Return (emails, career_page_url)."""
    emails: list[str] = []
    career_url = ""

    # Try job posting page first (sometimes has apply email)
    if job.job_url:
        for e in extract_emails_from_url(job.job_url):
            if e not in emails:
                emails.append(e)
        if emails:
            career_url = job.job_url

    urls = search_career_pages(company, max_results=6)
    for url in urls:
        if not career_url:
            career_url = url
        for e in extract_emails_from_url(url):
            if e not in emails:
                emails.append(e)
        if len(emails) >= 3:
            break
        time.sleep(0.5)

    # Guess website from first career URL
    website = ""
    if urls:
        from urllib.parse import urlparse

        netloc = urlparse(urls[0]).netloc
        if netloc:
            website = f"https://{netloc}"

    return emails[:5], career_url or (urls[0] if urls else "")


def run_pipeline(cfg: PipelineConfig) -> list[ContactRow]:
    sc = cfg.search
    print(
        f"Roles: {', '.join(sc.roles)} | Location: {sc.location!r} | "
        f"Experience: {sc.experience_min}-{sc.experience_max} years"
    )
    print(f"Sites ({len(sc.sites)}): {', '.join(sc.sites)}\n")

    jobs = search_all_jobs(cfg.search)
    if not jobs:
        print("No job listings found. Try a broader role or different location.")
        return []

    print(f"\nTotal unique listings: {len(jobs)}")
    print(f"Looking up career/HR emails (up to {cfg.max_companies} companies)...\n")

    rows: list[ContactRow] = []
    companies_done: set[str] = set()

    for job in jobs:
        key = job.company.lower()
        if key in companies_done:
            continue
        if len(companies_done) >= cfg.max_companies:
            break

        companies_done.add(key)
        print(f"  [{len(companies_done)}/{cfg.max_companies}] {job.company} — {job.job_title[:50]}")

        emails, career_page = find_emails_for_company(job.company, job)
        website = ""
        if career_page:
            from urllib.parse import urlparse

            netloc = urlparse(career_page).netloc
            if netloc:
                website = f"https://{netloc.replace('www.', '')}"

        if emails:
            primary = emails[0]
            extra = ", ".join(emails[1:cfg.emails_per_company])
            email_cell = primary if not extra else f"{primary}, {extra}"
            print(f"    -> {email_cell}")
        else:
            email_cell = "NO email id"
            print("    -> no email found on career pages")

        exp_label = f"{sc.experience_min}-{sc.experience_max} years"
        rows.append(
            ContactRow(
                company=job.company,
                email=email_cell,
                website=website,
                job_title=job.job_title,
                job_url=job.job_url,
                career_page=career_page,
                source=job.source,
                location=job.location,
                role_searched=job.role_searched,
                experience_range=exp_label,
                status="",
            )
        )

        if cfg.delay_seconds > 0:
            time.sleep(cfg.delay_seconds)

    return rows


def write_excel(rows: list[ContactRow], path: Path) -> None:
    data = {
        "Comapany Name": [r.company for r in rows],
        "EmailID": [r.email for r in rows],
        "Website": [r.website for r in rows],
        "Job Title": [r.job_title for r in rows],
        "Role Searched": [r.role_searched for r in rows],
        "Experience": [r.experience_range for r in rows],
        "Job URL": [r.job_url for r in rows],
        "Career Page": [r.career_page for r in rows],
        "Source": [r.source for r in rows],
        "Location": [r.location for r in rows],
        "Status": [r.status for r in rows],
    }
    df = pd.DataFrame(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(path, index=False)
    print(f"\nWrote {len(rows)} row(s) to {path.resolve()}")
