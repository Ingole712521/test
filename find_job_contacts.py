"""
Find job openings across many boards, filter by experience, extract HR emails → Excel.

Default: React Developer + DevOps Engineer, 1-4 years, India, all major sites.

Usage:
  pip install -r requirements.txt
  python find_job_contacts.py
  python find_job_contacts.py --roles "React Developer,DevOps Engineer" --experience-min 1 --experience-max 4
  python find_job_contacts.py --sites naukri indeed linkedin glassdoor foundit reddit remoteok --limit 50

Then:
  python send_mail_merge.py --excel Company_email.xlsx --template email_template.txt
"""

from __future__ import annotations

import argparse
from pathlib import Path

from job_hunter.pipeline import PipelineConfig, run_pipeline, write_excel
from job_hunter.search import DEFAULT_SITES, JOB_SITES, SearchConfig


def parse_roles(raw: str | None, single_role: str | None) -> list[str]:
    if raw:
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if parts:
            return parts
    if single_role:
        return [single_role.strip()]
    return ["React Developer", "DevOps Engineer"]


def main() -> None:
    all_sites = ", ".join(JOB_SITES)
    parser = argparse.ArgumentParser(
        description="Search job boards (Naukri, Indeed, LinkedIn, Glassdoor, Foundit, "
        "Reddit, remote boards), filter 1-4 yrs experience, extract HR emails"
    )
    parser.add_argument(
        "--roles",
        default=None,
        help='Comma-separated roles (default: "React Developer,DevOps Engineer")',
    )
    parser.add_argument(
        "--role",
        default=None,
        help="Single role shorthand (alternative to --roles)",
    )
    parser.add_argument(
        "--location",
        default="India",
        help="Location in search (default: India)",
    )
    parser.add_argument(
        "--sites",
        default=",".join(DEFAULT_SITES),
        help=f"Comma-separated sites. Available: {all_sites}",
    )
    parser.add_argument(
        "--experience-min",
        type=int,
        default=1,
        metavar="N",
        help="Minimum years of experience to target (default: 1)",
    )
    parser.add_argument(
        "--experience-max",
        type=int,
        default=4,
        metavar="N",
        help="Maximum years of experience to target (default: 4)",
    )
    parser.add_argument(
        "--results-per-site",
        type=int,
        default=10,
        metavar="N",
        help="Max search results per site per role (default: 10)",
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
        help="Output Excel path (default: Company_email.xlsx)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Seconds between company lookups (default: 1.5)",
    )
    parser.add_argument(
        "--no-remote-sites",
        action="store_true",
        help="Skip remoteok, remotive, weworkremotely, remoteco",
    )
    args = parser.parse_args()

    if args.experience_min > args.experience_max:
        raise SystemExit("--experience-min cannot be greater than --experience-max")

    sites = [s.strip().lower() for s in args.sites.split(",") if s.strip()]
    if args.no_remote_sites:
        remote = {"remoteok", "remotive", "weworkremotely", "remoteco"}
        sites = [s for s in sites if s not in remote]

    roles = parse_roles(args.roles, args.role)
    search_cfg = SearchConfig(
        roles=roles,
        location=args.location,
        sites=sites,
        results_per_site=args.results_per_site,
        experience_min=args.experience_min,
        experience_max=args.experience_max,
    )
    pipe_cfg = PipelineConfig(
        search=search_cfg,
        delay_seconds=args.delay,
        max_companies=args.limit,
    )

    print(f"Output: {args.output.resolve()}\n")

    rows = run_pipeline(pipe_cfg)
    if not rows:
        raise SystemExit(1)

    write_excel(rows, args.output)
    with_email = sum(1 for r in rows if r.email and "no email" not in r.email.lower())
    print(f"Companies with at least one email: {with_email}/{len(rows)}")
    print("\nNext step:")
    print(f'  python send_mail_merge.py --excel "{args.output}" --template email_template.txt')


if __name__ == "__main__":
    main()
