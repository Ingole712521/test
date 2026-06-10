from __future__ import annotations

import re

import scrapy

from remote_scraper.spiders.base import RemoteJobSpider


class WeWorkRemotelySpider(RemoteJobSpider):
    name = "weworkremotely"
    allowed_domains = ["weworkremotely.com"]

    RSS_FEEDS = (
        "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
        "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-front-end-programming-jobs.rss",
    )

    def start_requests(self):
        for feed in self.RSS_FEEDS:
            yield scrapy.Request(feed, callback=self.parse_rss, dont_filter=True)

    def parse_rss(self, response):
        count = 0
        for item in response.xpath("//item"):
            title = (item.xpath("title/text()").get() or "").strip()
            link = (item.xpath("link/text()").get() or "").strip()
            description = (item.xpath("description/text()").get() or "").strip()
            company, job_title = self._split_title(title)
            if not company:
                continue
            row = self.make_item(
                company=company,
                job_title=job_title,
                job_url=link,
                source="weworkremotely",
                snippet=description,
            )
            if row:
                count += 1
                yield row
            if count >= self.max_results:
                return

    @staticmethod
    def _split_title(title: str) -> tuple[str, str]:
        if ":" in title:
            company, rest = title.split(":", 1)
            job_title = rest.split(" - ")[0].strip()
            return company.strip(), job_title
        m = re.match(r"^(.+?)\s+at\s+(.+)$", title, re.I)
        if m:
            return m.group(2).strip(), m.group(1).strip()
        return "", title
