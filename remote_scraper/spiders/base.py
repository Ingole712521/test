from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote_plus

import scrapy

from job_hunter.experience import text_matches_experience
from job_hunter.search import JobListing, _clean_company, _role_matches_search
from remote_scraper.items import RemoteJobItem

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class RemoteJobSpider(scrapy.Spider):
    """Shared filtering and item building for remote job board spiders."""

    experience_min = 1
    experience_max = 4
    max_results = 25

    custom_settings = {
        "DOWNLOAD_DELAY": 1.5,
    }

    async def start(self):
        """Scrapy 2.13+ entry point; delegates to ``start_requests``."""
        for request in self.start_requests():
            yield request

    def start_requests(self):
        return iter(())

    def __init__(
        self,
        roles: str | None = None,
        experience_min: str | int = 1,
        experience_max: str | int = 4,
        max_results: str | int = 25,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        if roles:
            self.roles = [r.strip() for r in roles.split(",") if r.strip()]
        else:
            self.roles = ["React Developer", "DevOps Engineer"]
        self.experience_min = int(experience_min)
        self.experience_max = int(experience_max)
        self.max_results = int(max_results)

    def role_query(self, role: str) -> str:
        return quote_plus(role)

    def make_item(
        self,
        company: str,
        job_title: str,
        job_url: str,
        source: str,
        *,
        snippet: str = "",
        location: str = "Remote",
        company_url: str = "",
        role_searched: str = "",
    ) -> RemoteJobItem | None:
        company = _clean_company(company)
        job_title = re.sub(r"\s+", " ", (job_title or "").strip())
        if not company or not job_title:
            return None

        matched_role = role_searched
        if not matched_role:
            for role in self.roles:
                if _role_matches_search(role, job_title, snippet):
                    matched_role = role
                    break
        if not matched_role:
            return None

        blob = f"{job_title} {snippet}"
        if not text_matches_experience(blob, self.experience_min, self.experience_max):
            return None

        return RemoteJobItem(
            company=company,
            job_title=job_title,
            job_url=job_url or "",
            source=source,
            location=location or "Remote",
            role_searched=matched_role,
            snippet=(snippet or "")[:500],
            company_url=company_url or "",
        )

    def job_listing_to_item(self, job: JobListing) -> RemoteJobItem | None:
        return self.make_item(
            company=job.company,
            job_title=job.job_title,
            job_url=job.job_url,
            source=job.source,
            snippet=job.snippet,
            location=job.location or "Remote",
            role_searched=job.role_searched,
        )
