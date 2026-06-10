from __future__ import annotations

import json

import scrapy

from remote_scraper.spiders.base import RemoteJobSpider, USER_AGENT


class RemoteOkSpider(RemoteJobSpider):
    name = "remoteok"
    allowed_domains = ["remoteok.com"]

    def start_requests(self):
        yield scrapy.Request(
            "https://remoteok.com/api",
            headers={"User-Agent": USER_AGENT, "Referer": "https://remoteok.com/"},
            callback=self.parse_api,
            dont_filter=True,
        )

    def parse_api(self, response):
        try:
            jobs = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.warning("RemoteOK API returned invalid JSON")
            return

        count = 0
        for job in jobs:
            if not isinstance(job, dict):
                continue
            company = (job.get("company") or "").strip()
            title = (job.get("position") or job.get("title") or "").strip()
            url = (job.get("url") or job.get("apply_url") or "").strip()
            if url and not url.startswith("http"):
                url = f"https://remoteok.com{url}"
            snippet = (job.get("description") or "")[:500]
            location = (job.get("location") or "Remote").strip()
            company_url = (job.get("company_url") or "").strip()

            item = self.make_item(
                company=company,
                job_title=title,
                job_url=url,
                source="remoteok",
                snippet=snippet,
                location=location,
                company_url=company_url,
            )
            if item:
                count += 1
                yield item
            if count >= self.max_results:
                break
