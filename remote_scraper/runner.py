from __future__ import annotations

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from job_hunter.search import JobListing
from remote_scraper.collector import clear_collected_items, get_collected_items
from remote_scraper.spiders import SPIDER_MAP


def items_to_jobs(items: list[dict]) -> list[JobListing]:
    jobs: list[JobListing] = []
    seen: set[tuple[str, str, str]] = set()
    for row in items:
        company = (row.get("company") or "").strip()
        title = (row.get("job_title") or "").strip()
        role = (row.get("role_searched") or "").strip()
        if not company or not title:
            continue
        key = (company.lower(), title.lower()[:50], role.lower())
        if key in seen:
            continue
        seen.add(key)
        jobs.append(
            JobListing(
                company=company,
                job_title=title,
                location=(row.get("location") or "Remote").strip(),
                job_url=(row.get("job_url") or "").strip(),
                source=(row.get("source") or "").strip(),
                role_searched=role,
                snippet=(row.get("snippet") or "")[:500],
            )
        )
    return jobs


def run_remote_scrapers(
    sites: list[str],
    roles: list[str],
    *,
    experience_min: int = 1,
    experience_max: int = 4,
    max_results_per_site: int = 25,
) -> list[JobListing]:
    """Run Scrapy spiders for the given remote job boards."""
    clear_collected_items()
    unknown = [s for s in sites if s not in SPIDER_MAP]
    if unknown:
        print(f"Skipping unknown sites: {', '.join(unknown)}")
        print(f"Available: {', '.join(SPIDER_MAP)}")

    selected = [s for s in sites if s in SPIDER_MAP]
    if not selected:
        print("No valid Scrapy sites selected.")
        return []

    settings = get_project_settings()
    process = CrawlerProcess(settings)
    spider_kwargs = {
        "roles": ",".join(roles),
        "experience_min": experience_min,
        "experience_max": experience_max,
        "max_results": max_results_per_site,
    }
    for site in selected:
        print(f"  Crawling {site}...")
        process.crawl(SPIDER_MAP[site], **spider_kwargs)

    process.start()
    items = get_collected_items()
    jobs = items_to_jobs(items)
    print(f"\nScrapy collected {len(items)} item(s) -> {len(jobs)} unique job(s).")
    return jobs
