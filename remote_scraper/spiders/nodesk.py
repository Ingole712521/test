from __future__ import annotations

import re

import scrapy
from scrapy.selector import Selector

from remote_scraper.spiders.base import RemoteJobSpider, USER_AGENT


class NoDeskSpider(RemoteJobSpider):
    name = "nodesk"
    allowed_domains = ["nodesk.co"]

    FEEDS = (
        "https://nodesk.co/remote-jobs/engineering/index.xml",
        "https://nodesk.co/remote-jobs/devops/index.xml",
        "https://nodesk.co/remote-jobs/customer-support/index.xml",
    )

    def start_requests(self):
        for feed in self.FEEDS:
            yield scrapy.Request(
                feed,
                headers={"User-Agent": USER_AGENT},
                callback=self.parse_rss,
                dont_filter=True,
            )

    def parse_rss(self, response):
        try:
            sel = Selector(text=response.text, type="xml")
        except Exception:
            sel = Selector(text=response.text)

        count = 0
        for item in sel.xpath("//item"):
            title = (item.xpath("title/text()").get() or "").strip()
            link = (item.xpath("link/text()").get() or "").strip()
            description = (item.xpath("description/text()").get() or "").strip()
            company, job_title = self._split_title(title)
            row = self.make_item(
                company=company,
                job_title=job_title,
                job_url=link,
                source="nodesk",
                snippet=description,
            )
            if row:
                count += 1
                yield row
            if count >= self.max_results:
                return

    @staticmethod
    def _split_title(title: str) -> tuple[str, str]:
        # "Acme — Senior DevOps Engineer" or "Senior DevOps Engineer at Acme"
        if " — " in title:
            left, right = title.split(" — ", 1)
            if len(left) < 40:
                return left.strip(), right.strip()
        m = re.search(r"\bat\s+(.+)$", title, re.I)
        if m:
            return m.group(1).strip(), title[: m.start()].strip()
        return "", title
