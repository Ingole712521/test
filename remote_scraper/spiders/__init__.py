from remote_scraper.spiders.indeed import IndeedSpider
from remote_scraper.spiders.naukri import NaukriSpider
from remote_scraper.spiders.nodesk import NoDeskSpider
from remote_scraper.spiders.remoteok import RemoteOkSpider
from remote_scraper.spiders.remoteco import RemoteCoSpider
from remote_scraper.spiders.remotive import RemotiveSpider
from remote_scraper.spiders.weworkremotely import WeWorkRemotelySpider
from remote_scraper.spiders.workingnomads import WorkingNomadsSpider

SPIDER_MAP = {
    "remoteok": RemoteOkSpider,
    "remotive": RemotiveSpider,
    "weworkremotely": WeWorkRemotelySpider,
    "remoteco": RemoteCoSpider,
    "nodesk": NoDeskSpider,
    "workingnomads": WorkingNomadsSpider,
    "indeed": IndeedSpider,
    "naukri": NaukriSpider,
}

DEFAULT_REMOTE_SITES = list(SPIDER_MAP.keys())

__all__ = ["SPIDER_MAP", "DEFAULT_REMOTE_SITES"]
