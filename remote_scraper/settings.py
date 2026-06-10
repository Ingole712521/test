BOT_NAME = "remote_scraper"
SPIDER_MODULES = ["remote_scraper.spiders"]
NEWSPIDER_MODULE = "remote_scraper.spiders"

ROBOTSTXT_OBEY = False
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 1.5
DOWNLOAD_TIMEOUT = 45
RETRY_TIMES = 2
LOG_LEVEL = "INFO"

DEFAULT_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

ITEM_PIPELINES = {
    "remote_scraper.collector.CollectorPipeline": 300,
}
