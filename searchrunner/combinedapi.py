import json
from operator import itemgetter
import logging

import grequests
from searchrunner.scrapers import (COMBINED_API_PORT, PROVIDER_BASE_ROUTE,
                                   SCRAPER_MAP, REQUIRED_RESULT_KEYS)
from tornado import gen, ioloop, web

logger = logging.getLogger('combined_api')


class CombinedApiHandler(web.RequestHandler):
    """Handles combined response for provider API requests asynchronously."""

    def url_from_provider(self, provider):
        """Create an HTTP address from a provider name.

        Args:
            provider (str): Name of travel itinerary provider.

        Returns:
            str: Formatted HTTP address string.
        """
        provider_url = "{0}/scrapers/{1}".format(
            PROVIDER_BASE_ROUTE, provider.lower()
        )
        return provider_url

    def sort_in_place_by_agony(self, input_list):
        """Modify original input list reference by sorting in ascending order.

        Args:
            input_list (list): Reference to serialized list of flight results.
        """
        input_list.sort(key=itemgetter("agony"))

    def result_is_valid(self, result):
        """Validate individual flight result from provider API response.

        Args:
            result (dict): Individual provider API response result.

        Returns:
            bool: True if result is valid, False otherwise.
        """
        if type(result) == dict and (REQUIRED_RESULT_KEYS) <= set(result):
            return True
        else:
            return False

    @gen.coroutine
    def get(self):
        """Combine results of multiple provider API scrapes, maintaining
            agony sort for all combined results.

        Returns:
            An HTTP response, containing a jsonified dict of a list results
                and malformed results. An example of a successful response is:

            {
                "results": [
                    {
                        "agony": 1.8009004502251125, "price": 1999,
                        "provider": "Priceline",
                        "arrive_time": "2017-04-16T20:51:00",
                        "flight_num": "UA1001",
                        "depart_time": "2017-04-16T19:51:00"
                    },
                    ...
                ],
                "malformed_results": [...]
            }
        """
        combined_results = []
        malformed_results = []
        provider_urls = []

        # http://127.0.0.1:8000/flights/search?providers=united&providers=expedia # noqa
        defined_providers = self.get_arguments("providers")

        if not defined_providers:
            provider_urls = [
                self.url_from_provider(p) for p in SCRAPER_MAP.iterkeys()
            ]
        else:
            provider_urls = [
                self.url_from_provider(p) for p in defined_providers
            ]

        provider_requests = (grequests.get(
            u, stream=False, timeout=3) for u in provider_urls)  # n

        responses = grequests.map(provider_requests)  # send them all at once

        for response in responses:  # one per provider => O(nm)
            if response:  # grequests can return None if target is down
                if response.status_code == 200:
                    logger.info("{0} - {1}".format(
                        response.status_code, response.request.url))

                    try:
                        results = json.loads(response.content)["results"]  # m
                        for result in results:
                            if self.result_is_valid(result):
                                combined_results.append(result)
                                logger.info(result)
                            else:
                                malformed_results.append(result)
                                logger.warning(result)
                    except (KeyError, AttributeError, ValueError) as error:
                        logger.error(error)

                elif response.status_code == 404:
                    logger.error("{0} - {1}".format(
                        response.status_code, response.request.url))
                else:
                    logger.error("{0} - {1}".format(
                        response.status_code, response.request.url))
                response.close

        self.sort_in_place_by_agony(combined_results)  # Timsort => O(nlogn)

        self.write({
            "results": [r for r in combined_results],
            "malformed_results": [r for r in malformed_results]
        })


ROUTES = [
    (r"/flights/search", CombinedApiHandler),
]


def run():
    app = web.Application(
        ROUTES,
        debug=True,
    )

    app.listen(COMBINED_API_PORT)
    print "Server (re)started. Listening on port {0}".format(COMBINED_API_PORT)

    ioloop.IOLoop.current().start()


if __name__ == "__main__":
    logger.setLevel(logging.ERROR)  # change to INFO for explicit logs
    ch = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.propagate = False
    run()
