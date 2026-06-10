from __future__ import annotations

import scrapy

from job_hunter.search import SearchConfig, search_jobs_on_site
from remote_scraper.spiders.base import RemoteJobSpider


class IndeedSpider(RemoteJobSpider):
    """
    Indeed blocks automated page fetches (403). Uses web-search discovery only and
    emits jobs without requesting in.indeed.com / indeed.com job pages.
    """

    name = "indeed"

    def start_requests(self):
        jobs = self._search_jobs()
        yield scrapy.Request(
            "data:,",
            callback=self._emit_jobs,
            dont_filter=True,
            meta={"jobs": jobs},
        )

    def _search_jobs(self):
        cfg = SearchConfig(
            roles=self.roles,
            location="Remote",
            sites=["indeed"],
            results_per_site=self.max_results,
            experience_min=self.experience_min,
            experience_max=self.experience_max,
        )
        jobs = []
        seen_urls: set[str] = set()
        for role in self.roles:
            for job in search_jobs_on_site(cfg, "indeed", role, self.max_results):
                if job.job_url and job.job_url in seen_urls:
                    continue
                if job.job_url:
                    seen_urls.add(job.job_url)
                jobs.append(job)
        return jobs

    def _emit_jobs(self, response):
        jobs = response.meta.get("jobs") or []
        if not jobs:
            self.logger.warning("No Indeed listings found via search.")
            return

        count = 0
        seen: set[tuple[str, str]] = set()
        for job in jobs:
            key = (job.company.lower(), job.job_title.lower()[:50])
            if key in seen:
                continue
            seen.add(key)
            item = self.job_listing_to_item(job)
            if item:
                count += 1
                yield item
            if count >= self.max_results:
                break
