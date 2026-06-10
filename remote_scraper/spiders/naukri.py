from __future__ import annotations

import scrapy

from job_hunter.search import SearchConfig, search_jobs_on_site
from remote_scraper.spiders.base import RemoteJobSpider


class NaukriSpider(RemoteJobSpider):
    """
    Naukri is heavily JavaScript-driven. Uses search-backed job discovery and
    parses listing pages when HTML is available.
    """

    name = "naukri"
    allowed_domains = ["naukri.com"]

    custom_settings = {
        "HTTPERROR_ALLOWED_CODES": [403, 404, 410, 429, 503],
    }

    def start_requests(self):
        for role in self.roles:
            query = self.role_query(role)
            url = f"https://www.naukri.com/{query.replace('+', '-')}-jobs?k={query}&jobType=remote"
            yield scrapy.Request(
                url,
                callback=self.parse_listing,
                errback=self._search_fallback,
                cb_kwargs={"role": role},
                dont_filter=True,
            )

    def parse_listing(self, response, role: str):
        if response.status != 200:
            self.logger.warning(
                "Naukri returned HTTP %s for %s; using search fallback",
                response.status,
                response.url,
            )
            yield from self._emit_search_jobs(role)
            return
        count = 0
        for row in response.css("article.jobTuple, div.cust-job-tuple, .srp-jobtuple"):
            title = (row.css("a.title::text, .title::text").get() or "").strip()
            link = row.css("a.title::attr(href), a::attr(href)").get()
            company = (row.css(".comp-name::text, .companyInfo .empWrapper a::text").get() or "").strip()
            if link and not link.startswith("http"):
                link = response.urljoin(link)
            item = self.make_item(
                company=company,
                job_title=title,
                job_url=link or "",
                source="naukri",
                role_searched=role,
            )
            if item:
                count += 1
                yield item
            if count >= self.max_results:
                return

        if count == 0:
            yield from self._emit_search_jobs(role)

    def _search_fallback(self, failure, role: str):  # noqa: ANN001
        self.logger.warning("Naukri listing failed (%s); using search fallback", failure.value)
        yield from self._emit_search_jobs(role)

    def _emit_search_jobs(self, role: str):
        cfg = SearchConfig(
            roles=[role],
            location="Remote",
            sites=["naukri"],
            results_per_site=self.max_results,
            experience_min=self.experience_min,
            experience_max=self.experience_max,
        )
        for job in search_jobs_on_site(cfg, "naukri", role, self.max_results):
            item = self.job_listing_to_item(job)
            if item:
                yield item
