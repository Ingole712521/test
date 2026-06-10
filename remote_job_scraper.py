"""
Scrapy-based remote job pipeline:
  1. Scrape remote job boards (Indeed, Naukri, RemoteOK, Remotive, We Work Remotely,
     remote.co, NoDesk, Working Nomads, …)
  2. Look up each company's career / HR / info email
  3. Write Company_email.xlsx
  4. Optionally send outreach emails via Gmail

Usage:
  pip install -r requirements.txt
  python remote_job_scraper.py

  python remote_job_scraper.py --roles "DevOps Engineer,React Developer" --limit 30
  python remote_job_scraper.py --sites remoteok,remotive,weworkremotely --dry-run
  python remote_job_scraper.py --send --template email_template.txt
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from job_hunter.pipeline import ContactRow, find_emails_for_company, write_excel
from remote_scraper.runner import run_remote_scrapers
from remote_scraper.spiders import DEFAULT_REMOTE_SITES


def parse_roles(raw: str | None, single_role: str | None) -> list[str]:
    if raw:
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if parts:
            return parts
    if single_role:
        return [single_role.strip()]
    return ["React Developer", "DevOps Engineer"]


def build_contact_rows(
    jobs,
    *,
    experience_min: int,
    experience_max: int,
    max_companies: int,
    delay_seconds: float,
    emails_per_company: int,
) -> list[ContactRow]:
    rows: list[ContactRow] = []
    companies_done: set[str] = set()
    exp_label = f"{experience_min}-{experience_max} years"

    print(f"\nLooking up career / HR / info emails (up to {max_companies} companies)...\n")

    for job in jobs:
        key = job.company.lower()
        if key in companies_done:
            continue
        if len(companies_done) >= max_companies:
            break

        companies_done.add(key)
        print(f"  [{len(companies_done)}/{max_companies}] {job.company} — {job.job_title[:50]}")

        emails, career_page = find_emails_for_company(job.company, job)
        website = job.job_url or career_page
        if career_page:
            from urllib.parse import urlparse

            netloc = urlparse(career_page).netloc
            if netloc:
                website = f"https://{netloc.replace('www.', '')}"

        if emails:
            primary = emails[0]
            extra = ", ".join(emails[1:emails_per_company])
            email_cell = primary if not extra else f"{primary}, {extra}"
            print(f"    -> {email_cell}")
        else:
            email_cell = "NO email id"
            print("    -> no email found")

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

        if delay_seconds > 0:
            import time

            time.sleep(delay_seconds)

    return rows


def main() -> None:
    sites_help = ", ".join(DEFAULT_REMOTE_SITES)
    parser = argparse.ArgumentParser(
        description="Scrapy: scrape remote job boards, find company emails, optional Gmail send"
    )
    parser.add_argument(
        "--roles",
        default=None,
        help='Comma-separated roles (default: "React Developer,DevOps Engineer")',
    )
    parser.add_argument("--role", default=None, help="Single role shorthand")
    parser.add_argument(
        "--sites",
        default=",".join(DEFAULT_REMOTE_SITES),
        help=f"Comma-separated boards. Available: {sites_help}",
    )
    parser.add_argument("--experience-min", type=int, default=1, metavar="N")
    parser.add_argument("--experience-max", type=int, default=4, metavar="N")
    parser.add_argument(
        "--results-per-site",
        type=int,
        default=25,
        metavar="N",
        help="Max jobs per board per role (default: 25)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        metavar="N",
        help="Max companies to look up for emails (default: 50)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("Company_email.xlsx"),
        help="Output Excel path",
    )
    parser.add_argument("--delay", type=float, default=1.5, help="Delay between email lookups")
    parser.add_argument(
        "--scrape-only",
        action="store_true",
        help="Only scrape jobs; skip email lookup and Excel write",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape jobs and print summary; skip email lookup",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="After Excel is written, run send_mail_merge.py",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=Path("email_template.txt"),
        help="Email template for --send",
    )
    parser.add_argument(
        "--mail-limit",
        type=int,
        default=50,
        metavar="N",
        help="Max rows to email when using --send (passed to send_mail_merge.py)",
    )
    args = parser.parse_args()

    if args.experience_min > args.experience_max:
        raise SystemExit("--experience-min cannot be greater than --experience-max")

    roles = parse_roles(args.roles, args.role)
    sites = [s.strip().lower() for s in args.sites.split(",") if s.strip()]

    print("Remote job scraper (Scrapy)")
    print(f"Roles: {', '.join(roles)}")
    print(f"Experience: {args.experience_min}-{args.experience_max} years")
    print(f"Sites: {', '.join(sites)}\n")

    jobs = run_remote_scrapers(
        sites=sites,
        roles=roles,
        experience_min=args.experience_min,
        experience_max=args.experience_max,
        max_results_per_site=args.results_per_site,
    )
    if not jobs:
        raise SystemExit("No jobs found. Try different roles or sites.")

    if args.scrape_only or args.dry_run:
        print(f"\nFound {len(jobs)} job listing(s):")
        for job in jobs[:30]:
            print(f"  [{job.source}] {job.company} — {job.job_title}")
        if len(jobs) > 30:
            print(f"  ... and {len(jobs) - 30} more")
        if args.dry_run:
            print("\nDry run — skipping email lookup.")
        return

    rows = build_contact_rows(
        jobs,
        experience_min=args.experience_min,
        experience_max=args.experience_max,
        max_companies=args.limit,
        delay_seconds=args.delay,
        emails_per_company=3,
    )
    if not rows:
        raise SystemExit("No companies processed.")

    write_excel(rows, args.output)
    with_email = sum(1 for r in rows if r.email and "no email" not in r.email.lower())
    print(f"\nCompanies with at least one email: {with_email}/{len(rows)}")

    if args.send:
        cmd = [
            sys.executable,
            str(Path(__file__).resolve().parent / "send_mail_merge.py"),
            "--excel",
            str(args.output.resolve()),
            "--template",
            str(args.template.resolve()),
            "--limit",
            str(args.mail_limit),
        ]
        print("\nSending emails...")
        subprocess.run(cmd, check=False)
    else:
        print("\nNext step:")
        print(f'  python send_mail_merge.py --excel "{args.output}" --template email_template.txt')
        print("Or run this script with --send to scrape, find emails, and send in one go.")


if __name__ == "__main__":
    main()
