from __future__ import annotations

import json

import scrapy

from remote_scraper.spiders.base import RemoteJobSpider, USER_AGENT


class RemotiveSpider(RemoteJobSpider):
    name = "remotive"
    allowed_domains = ["remotive.com", "remotive.io"]

    def start_requests(self):
        for role in self.roles:
            query = self.role_query(role)
            url = f"https://remotive.com/api/remote-jobs?search={query}&limit={self.max_results}"
            yield scrapy.Request(
                url,
                headers={"User-Agent": USER_AGENT},
                callback=self.parse_api,
                cb_kwargs={"role": role},
                dont_filter=True,
            )

    def parse_api(self, response, role: str):
        try:
            payload = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.warning("Remotive API returned invalid JSON")
            return

        jobs = payload.get("jobs") or []
        count = 0
        for job in jobs:
            if not isinstance(job, dict):
                continue
            company = (job.get("company_name") or "").strip()
            title = (job.get("title") or "").strip()
            url = (job.get("url") or "").strip()
            snippet = (job.get("description") or "")[:500]
            location = (job.get("candidate_required_location") or "Remote").strip()
            item = self.make_item(
                company=company,
                job_title=title,
                job_url=url,
                source="remotive",
                snippet=snippet,
                location=location,
                role_searched=role,
            )
            if item:
                count += 1
                yield item
            if count >= self.max_results:
                break
