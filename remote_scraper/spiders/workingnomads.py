from __future__ import annotations

import json
import re

import scrapy

from remote_scraper.spiders.base import RemoteJobSpider, USER_AGENT


class WorkingNomadsSpider(RemoteJobSpider):
    name = "workingnomads"
    allowed_domains = ["workingnomads.com", "workingnomads.co"]

    CATEGORY_MAP = {
        "react": "development",
        "developer": "development",
        "devops": "devops",
        "engineer": "development",
        "frontend": "development",
        "backend": "development",
    }

    def start_requests(self):
        categories: set[str] = set()
        for role in self.roles:
            low = role.lower()
            matched = False
            for key, cat in self.CATEGORY_MAP.items():
                if key in low:
                    categories.add(cat)
                    matched = True
            if not matched:
                categories.add("development")
        if not categories:
            categories = {"development", "devops"}

        for category in categories:
            url = f"https://www.workingnomads.com/api/exposed_jobs/?category={category}"
            yield scrapy.Request(
                url,
                headers={"User-Agent": USER_AGENT},
                callback=self.parse_api,
                dont_filter=True,
            )

    def parse_api(self, response):
        try:
            jobs = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.warning("Working Nomads API returned invalid JSON")
            return

        count = 0
        for job in jobs:
            if not isinstance(job, dict):
                continue
            company = (job.get("company_name") or "").strip()
            title = (job.get("title") or "").strip()
            url = (job.get("url") or "").strip()
            snippet = re.sub(r"<[^>]+>", " ", job.get("description") or "")[:500]
            location = (job.get("location") or "Remote").strip()
            item = self.make_item(
                company=company,
                job_title=title,
                job_url=url,
                source="workingnomads",
                snippet=snippet,
                location=location,
            )
            if item:
                count += 1
                yield item
            if count >= self.max_results:
                break
