"""
Find AWS / DevOps jobs on LinkedIn (via public job listings), extract HR/career
emails from company pages and Google search, save to Excel.

Columns: Company Name | Email ID | Role

Note: This does not log into LinkedIn in a browser (LinkedIn blocks bots and
requires an account). It finds LinkedIn job postings through web search, then
looks up emails on career pages and Google — same reliable approach as
find_job_contacts.py.

Usage:
  pip install -r requirements.txt
  python linkedin_devops_jobs.py
  python linkedin_devops_jobs.py --location "Bangalore" --limit 30
  python linkedin_devops_jobs.py --experience-min 0 --experience-max 5
"""

from __future__ import annotations

import argparse
from pathlib import Path

from job_hunter.pipeline import PipelineConfig, run_pipeline, write_excel_simple
from job_hunter.search import SearchConfig

DEFAULT_DEVOPS_ROLES = [
    "AWS DevOps Engineer",
    "DevOps Engineer",
    "Junior DevOps Engineer",
    "DevOps Mid Level",
    "AWS Cloud Engineer",
    "AWS Engineer",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LinkedIn AWS/DevOps job search + HR email lookup → Excel"
    )
    parser.add_argument(
        "--roles",
        default=",".join(DEFAULT_DEVOPS_ROLES),
        help="Comma-separated job titles to search (default: AWS/DevOps variants)",
    )
    parser.add_argument(
        "--location",
        default="India",
        help="Job location for search (default: India)",
    )
    parser.add_argument(
        "--experience-min",
        type=int,
        default=0,
        metavar="N",
        help="Minimum years of experience (default: 0 for junior)",
    )
    parser.add_argument(
        "--experience-max",
        type=int,
        default=5,
        metavar="N",
        help="Maximum years of experience (default: 5 for mid-level)",
    )
    parser.add_argument(
        "--results-per-role",
        type=int,
        default=12,
        metavar="N",
        help="Max LinkedIn results per role (default: 12)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=40,
        metavar="N",
        help="Max companies to look up for emails (default: 40)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("Company_email.xlsx"),
        help="Output Excel file (default: Company_email.xlsx)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Seconds between company email lookups (default: 1.5)",
    )
    args = parser.parse_args()

    if args.experience_min > args.experience_max:
        raise SystemExit("--experience-min cannot be greater than --experience-max")

    roles = [r.strip() for r in args.roles.split(",") if r.strip()]
    if not roles:
        raise SystemExit("Provide at least one role via --roles")

    search_cfg = SearchConfig(
        roles=roles,
        location=args.location,
        sites=["linkedin"],
        results_per_site=args.results_per_role,
        experience_min=args.experience_min,
        experience_max=args.experience_max,
        remote_friendly=True,
    )
    pipe_cfg = PipelineConfig(
        search=search_cfg,
        delay_seconds=args.delay,
        max_companies=args.limit,
    )

    print("LinkedIn AWS / DevOps job contact finder")
    print(f"Roles: {', '.join(roles)}")
    print(f"Location: {args.location}")
    print(
        f"Experience: {args.experience_min}-{args.experience_max} years "
        "(junior to mid-level)"
    )
    print(f"Output: {args.output.resolve()}\n")

    rows = run_pipeline(pipe_cfg)
    if not rows:
        raise SystemExit(
            "No jobs or emails found. Try --location with a city name "
            "or broaden --experience-max."
        )

    write_excel_simple(rows, args.output)
    with_email = sum(
        1 for r in rows if r.email and "no email" not in r.email.lower()
    )
    print(f"Rows with at least one email: {with_email}/{len(rows)}")


if __name__ == "__main__":
    main()
