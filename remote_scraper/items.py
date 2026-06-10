from __future__ import annotations

import scrapy


class RemoteJobItem(scrapy.Item):
    company = scrapy.Field()
    job_title = scrapy.Field()
    job_url = scrapy.Field()
    source = scrapy.Field()
    location = scrapy.Field()
    role_searched = scrapy.Field()
    snippet = scrapy.Field()
    company_url = scrapy.Field()
