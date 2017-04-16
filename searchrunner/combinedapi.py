import json
from operator import itemgetter

import grequests
from searchrunner.scrapers import (COMBINED_API_PORT, PROVIDER_BASE_ROUTE,
                                   SCRAPER_MAP, REQUIRED_RESULT_KEYS)
from tornado import gen, ioloop, web


class CombinedApiHandler(web.RequestHandler):

    def url_from_provider(self, provider):
        provider_url = "{0}/scrapers/{1}".format(
            PROVIDER_BASE_ROUTE, provider.lower()
        )
        return provider_url

    def sort_in_place_by_agony(self, input_list):
        input_list.sort(key=itemgetter("agony"))

    def result_is_valid(self, result):
        if type(result) == dict and (REQUIRED_RESULT_KEYS) <= set(result):
            return True
        else:
            return False

    @gen.coroutine
    def get(self):

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

                    try:
                        results = json.loads(response.content)["results"]  # m
                        for result in results:
                            if self.result_is_valid(result):
                                combined_results.append(result)
                            else:
                                malformed_results.append(result)
                    except (KeyError, AttributeError, ValueError):
                        pass  # explicitly handle incorrect provider response

                elif response.status_code == 404:
                    pass  # explicitly handle provider error
                else:
                    pass  # explicitly handle other response code errors
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
    run()
