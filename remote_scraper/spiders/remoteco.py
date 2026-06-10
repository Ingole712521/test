from __future__ import annotations

import scrapy

from job_hunter.search import SearchConfig, search_jobs_on_site
from remote_scraper.spiders.base import RemoteJobSpider


class RemoteCoSpider(RemoteJobSpider):
    """
    remote.co often blocks direct scraping from some networks.
    Falls back to web search for remote.co job URLs when the site is unreachable.
    """

    name = "remoteco"
    allowed_domains = ["remote.co"]

    def start_requests(self):
        yield scrapy.Request(
            "https://remote.co/remote-jobs/",
            callback=self.parse_listing,
            errback=self._search_fallback,
            dont_filter=True,
        )

    def parse_listing(self, response):
        count = 0
        for card in response.css("div.job_listing, article.job, li.job_listing"):
            title = (
                card.css("h2 a::text, h3 a::text, .position a::text").get() or ""
            ).strip()
            link = card.css("h2 a::attr(href), h3 a::attr(href), .position a::attr(href)").get()
            company = (card.css(".company::text, .company strong::text").get() or "").strip()
            if not title and link:
                title = link.rstrip("/").split("/")[-1].replace("-", " ").title()
            if not company:
                company = (card.css("[class*=company]::text").get() or "").strip()
            if not link:
                continue
            if not link.startswith("http"):
                link = response.urljoin(link)
            item = self.make_item(
                company=company,
                job_title=title,
                job_url=link,
                source="remoteco",
            )
            if item:
                count += 1
                yield item
            if count >= self.max_results:
                return

        if count == 0:
            yield from self._emit_search_jobs()

    def _search_fallback(self, failure):  # noqa: ANN001
        self.logger.warning("remote.co listing failed (%s); using search fallback", failure.value)
        yield from self._emit_search_jobs()

    def _emit_search_jobs(self):
        cfg = SearchConfig(
            roles=self.roles,
            location="Remote",
            sites=["remoteco"],
            results_per_site=self.max_results,
            experience_min=self.experience_min,
            experience_max=self.experience_max,
        )
        for role in self.roles:
            for job in search_jobs_on_site(cfg, "remoteco", role, self.max_results):
                item = self.job_listing_to_item(job)
                if item:
                    yield item
