from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from ddgs import DDGS

from job_hunter.experience import experience_query_suffix, text_matches_experience

# All supported job sources (DuckDuckGo site: filters)
JOB_SITES: dict[str, str] = {
    "naukri": "site:naukri.com",
    "indeed": "site:indeed.com/viewjob OR site:in.indeed.com/viewjob",
    "linkedin": "site:linkedin.com/jobs/view",
    "glassdoor": "site:glassdoor.co.in OR site:glassdoor.com/job",
    "foundit": "site:foundit.in OR site:monsterindia.com",
    "reddit": "site:reddit.com",
    "remoteok": "site:remoteok.com",
    "remotive": "site:remotive.com",
    "weworkremotely": "site:weworkremotely.com",
    "remoteco": "site:remote.co",
    "remote": "site:remoteok.com OR site:remotive.com OR site:remote.co",
    "cutshort": "site:cutshort.io/job",
    "wellfound": "site:wellfound.com/jobs",
    "shine": "site:shine.com/jobs",
    "timesjobs": "site:timesjobs.com",
}

DEFAULT_SITES = [
    "naukri",
    "indeed",
    "linkedin",
    "glassdoor",
    "foundit",
    "reddit",
    "remoteok",
    "remotive",
    "weworkremotely",
    "remoteco",
]

AGGREGATOR_HOSTS = (
    "naukri",
    "indeed",
    "linkedin",
    "glassdoor",
    "foundit",
    "monsterindia",
    "internshala",
    "cutshort",
    "shine",
    "timesjobs",
    "wellfound",
    "reddit.com/r/",
    "remoteok",
    "remotive",
    "weworkremotely",
    "remote.co",
)

HIRING_TITLE = re.compile(
    r"^(.+?)\s+is\s+hiring\s+(.+?)(?:\s+job\s+in\s+|\s+in\s+)(.+?)(?:\s*\||\s*-|$)",
    re.IGNORECASE,
)
# LinkedIn: "Acme hiring DevOps Engineer in Bangalore, Karnataka, India | LinkedIn"
LINKEDIN_HIRING = re.compile(
    r"^(.+?)\s+hiring\s+(.+?)\s+in\s+(.+?)(?:\s*\|\s*LinkedIn)?$",
    re.IGNORECASE,
)
AT_TITLE = re.compile(r"^(.+?)\s+at\s+(.+?)(?:\s*\||\s*-|$)", re.IGNORECASE)
DASH_TITLE = re.compile(r"^(.+?)\s+-\s+(.+?)(?:\s*\||\s*-|$)")

ROLE_KEYWORDS: dict[str, re.Pattern] = {
    "react": re.compile(r"\b(react\.?js|react\s+js|react\s+developer|frontend)\b", re.I),
    "devops": re.compile(
        r"\b(devops|dev\s*ops|sre|site\s+reliability|platform\s+engineer|"
        r"cloud\s+engineer|infrastructure\s+engineer|junior\s+devops|"
        r"mid[\s-]?level\s+devops)\b",
        re.I,
    ),
    "aws": re.compile(
        r"\b(aws|amazon\s+web\s+services|cloud\s+aws|aws\s+devops|"
        r"aws\s+engineer|aws\s+cloud)\b",
        re.I,
    ),
}

BAD_URL_FRAGMENTS = (
    "naukri.com/python-developer-jobs",
    "naukri.com/job-listings",
    "naukri.com/react-developer-jobs",
    "naukri.com/devops-jobs",
    "/jobs-in-",
    "-jobs-in-",
    "indeed.com/jobs?",
    "indeed.com/q-",
    "reddit.com/r/forhire/comments/?",
    "glassdoor.co.in/Job/",
    "glassdoor.com/Job/india",
)


@dataclass
class JobListing:
    company: str
    job_title: str
    location: str
    job_url: str
    source: str
    role_searched: str = ""
    snippet: str = ""


@dataclass
class SearchConfig:
    roles: list[str] = field(default_factory=lambda: ["React Developer", "DevOps Engineer"])
    location: str = "India"
    sites: list[str] = field(default_factory=lambda: list(DEFAULT_SITES))
    results_per_site: int = 10
    experience_min: int = 1
    experience_max: int = 4
    remote_friendly: bool = True

    @property
    def role(self) -> str:
        """Backward compatibility: first role."""
        return self.roles[0] if self.roles else ""


JOB_TITLE_WORDS = re.compile(
    r"\b(developer|engineer|analyst|manager|architect|intern|consultant|"
    r"programmer|designer|lead|senior|junior|associate|vice president|vp|"
    r"director|specialist|technician|scientist)\b",
    re.I,
)


def _role_matches_search(role_searched: str, job_title: str, snippet: str) -> bool:
    blob = f"{role_searched} {job_title} {snippet}".lower()
    if "react" in role_searched.lower():
        return bool(ROLE_KEYWORDS["react"].search(blob))
    if "aws" in role_searched.lower():
        return bool(ROLE_KEYWORDS["aws"].search(blob)) or bool(
            ROLE_KEYWORDS["devops"].search(blob)
        )
    if "devops" in role_searched.lower():
        return bool(ROLE_KEYWORDS["devops"].search(blob))
    return role_searched.lower() in blob


def _parse_listing(
    title: str,
    url: str,
    source: str,
    role_searched: str,
    body: str = "",
) -> JobListing | None:
    title = re.sub(r"\s+", " ", title.strip())
    company = ""
    job_title = ""
    location = ""

    m = HIRING_TITLE.match(title)
    if m:
        company, job_title, location = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
    else:
        m = LINKEDIN_HIRING.match(title)
        if m:
            company, job_title, location = (
                m.group(1).strip(),
                m.group(2).strip(),
                m.group(3).strip(),
            )
    if not company:
        m = AT_TITLE.match(title)
        if m:
            job_title, company = m.group(1).strip(), m.group(2).strip()
        elif not company:
            m = DASH_TITLE.match(title)
            if m:
                company, job_title = m.group(1).strip(), m.group(2).strip()

    if not company and "/jobs/view/" in url.lower():
        slug = urlparse(url).path.rstrip("/").split("/")[-1]
        # e.g. devops-engineer-aws-at-lightcast-3497728904
        if "-at-" in slug:
            parts = slug.rsplit("-at-", 1)
            job_title = parts[0].replace("-", " ").title()
            company = parts[1].rsplit("-", 1)[0].replace("-", " ").title()

    if not company:
        host = urlparse(url).netloc.replace("www.", "")
        if any(x in host for x in AGGREGATOR_HOSTS):
            if source != "reddit":
                return None
        company = host.split(".")[0].title()

    if not job_title:
        job_title = title[:120]

    company = _clean_company(company)
    if not company or len(company) < 2:
        return None

    combined = f"{title} {body} {job_title}"
    if not _role_matches_search(role_searched, job_title, body):
        return None

    return JobListing(
        company=company,
        job_title=job_title,
        location=location,
        job_url=url,
        source=source,
        role_searched=role_searched,
        snippet=body[:300],
    )


def _clean_company(name: str) -> str:
    name = re.sub(r"\s+(Pvt\.?|Private|Limited|Ltd\.?|LLC|Inc\.?|Corp\.?)\s*$", "", name, flags=re.I)
    name = re.sub(r"\s+", " ", name).strip(" -|,")
    junk = {"NA", "N/A", "Company", "Employer", "Hiring", "Reddit", "Indeed", "Naukri"}
    if name.upper() in junk or len(name) < 2:
        return ""
    if JOB_TITLE_WORDS.search(name) and len(name) > 35:
        return ""
    if "\ufffd" in name:
        return ""
    low = name.lower()
    if any(
        bad in low
        for bad in (
            "naukri.com",
            "indeed.com",
            "linkedin",
            "glassdoor",
            "foundit",
            "reddit.com",
            "jobs in ",
            "job in ",
            "jobs at ",
            "hiring now",
            "remoteok",
            "remotive",
        )
    ):
        return ""
    return name


def _build_query(cfg: SearchConfig, site_key: str, role: str) -> str:
    site_filter = JOB_SITES.get(site_key, "")
    exp = experience_query_suffix(cfg.experience_min, cfg.experience_max)
    parts = [role, "jobs", cfg.location, exp, site_filter]
    if cfg.remote_friendly and site_key in ("remoteok", "remotive", "weworkremotely", "remoteco"):
        parts.insert(2, "remote")
    if site_key == "reddit":
        parts.insert(1, "hiring OR jobs OR [Hiring]")
    return " ".join(p for p in parts if p).strip()


def search_jobs_on_site(
    cfg: SearchConfig,
    site_key: str,
    role: str,
    max_results: int,
) -> list[JobListing]:
    query = _build_query(cfg, site_key, role)
    listings: list[JobListing] = []
    seen_urls: set[str] = set()

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
    except Exception as exc:
        print(f"  [{site_key}] search failed: {exc}")
        return []

    for r in results:
        url = (r.get("href") or "").strip()
        title = (r.get("title") or "").strip()
        body = (r.get("body") or "").strip()
        if not url or url in seen_urls:
            continue
        url_l = url.lower()
        if "linkedin.com/jobs/view" not in url_l and any(
            bad in url_l for bad in BAD_URL_FRAGMENTS
        ):
            continue
        if "linkedin.com/jobs" in url_l and "/jobs/view/" not in url_l:
            continue

        combined_text = f"{title} {body}"
        if not text_matches_experience(
            combined_text, cfg.experience_min, cfg.experience_max
        ):
            continue

        seen_urls.add(url)
        parsed = _parse_listing(title, url, site_key, role, body)
        if parsed:
            listings.append(parsed)

    return listings


def search_all_jobs(cfg: SearchConfig) -> list[JobListing]:
    all_jobs: list[JobListing] = []
    seen: set[tuple[str, str, str]] = set()

    for role in cfg.roles:
        role = role.strip()
        if not role:
            continue
        print(
            f"\n=== Role: {role!r} | experience {cfg.experience_min}-{cfg.experience_max} years ==="
        )
        for site in cfg.sites:
            site = site.strip().lower()
            if site not in JOB_SITES:
                print(f"  Skipping unknown site: {site!r} (use: {', '.join(JOB_SITES)})")
                continue
            print(f"  Searching {site}...")
            batch = search_jobs_on_site(cfg, site, role, cfg.results_per_site)
            print(f"    -> {len(batch)} listing(s)")
            for job in batch:
                key = (job.company.lower(), job.job_title.lower()[:40], role.lower())
                if key in seen:
                    continue
                seen.add(key)
                all_jobs.append(job)

    return all_jobs


def search_hr_emails_google(company: str, max_results: int = 8) -> list[str]:
    """Find HR/careers/recruitment emails via web search snippets and linked pages."""
    from job_hunter.emails import extract_emails_from_text, extract_emails_from_url

    queries = [
        f'"{company}" HR email careers recruitment hiring contact',
        f'"{company}" "careers@" OR "hr@" OR "jobs@" OR "recruitment@" email',
    ]
    emails: list[str] = []
    seen: set[str] = set()
    try:
        with DDGS() as ddgs:
            for query in queries:
                try:
                    results = list(ddgs.text(query, max_results=max_results))
                except Exception:
                    continue
                for r in results:
                    blob = f"{r.get('title', '')} {r.get('body', '')}"
                    for e in extract_emails_from_text(blob):
                        if e.lower() not in seen:
                            seen.add(e.lower())
                            emails.append(e)
                    url = (r.get("href") or "").strip()
                    if url.startswith("http"):
                        host = urlparse(url).netloc.lower()
                        if any(
                            s in host
                            for s in (
                                "linkedin.com",
                                "facebook.com",
                                "twitter.com",
                                "indeed.com",
                                "naukri.com",
                            )
                        ):
                            continue
                        for e in extract_emails_from_url(url):
                            if e.lower() not in seen:
                                seen.add(e.lower())
                                emails.append(e)
                if len(emails) >= 3:
                    break
    except Exception:
        return emails
    return emails


def search_career_pages(company: str, max_results: int = 5) -> list[str]:
    query = f'"{company}" careers jobs contact apply HR email'
    urls: list[str] = []
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
    except Exception:
        return []

    skip_hosts = AGGREGATOR_HOSTS + (
        "facebook.com",
        "twitter.com",
        "instagram.com",
        "youtube.com",
    )
    for r in results:
        url = (r.get("href") or "").strip()
        if not url.startswith("http"):
            continue
        host = urlparse(url).netloc.lower()
        if any(s in host for s in skip_hosts):
            continue
        if url not in urls:
            urls.append(url)
    return urls
