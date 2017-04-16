from searchrunner.scrapers.expedia import ExpediaScraper
from searchrunner.scrapers.orbitz import OrbitzScraper
from searchrunner.scrapers.priceline import PricelineScraper
from searchrunner.scrapers.travelocity import TravelocityScraper
from searchrunner.scrapers.united import UnitedScraper

PROVIDER_API_PORT = 9000
PROVIDER_BASE_ROUTE = "http://127.0.0.1:{0}".format(PROVIDER_API_PORT)
COMBINED_API_PORT = 8000
COMBINED_BASE_ROUTE = "http://127.0.0.1:{0}".format(COMBINED_API_PORT)
REQUIRED_RESULT_KEYS = set(("agony", "price", "provider",
                            "arrive_time", "flight_num", "depart_time"))
SCRAPERS = [
    ExpediaScraper,
    OrbitzScraper,
    PricelineScraper,
    TravelocityScraper,
    UnitedScraper,
]
SCRAPER_MAP = {s.provider.lower(): s for s in SCRAPERS}


def get_scraper(provider):
    return SCRAPER_MAP.get(provider.lower())
