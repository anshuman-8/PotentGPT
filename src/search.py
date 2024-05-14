# import os
import time
import json
import requests
import logging as log
import asyncio
from typing import Dict, List
from itertools import zip_longest

from src.config import Config
from src.model import Link, getLinkJsonList

## --- Alert ---
LOG_FILES = False  # Set to True to log the results to files

config = Config()

class Search:
    def __init__(
        self,
        web_queries: List[str],
        yelp_query: str,
        gmaps_query: str,
        location: str,
        country_code: str,
        timeout: int,
        web_search: bool = True,
        yelp_search: bool = True,
        gmap_search: bool = True,
    ):
        self.web_queries = web_queries
        self.yelp_query = yelp_query
        self.gmaps_query = gmaps_query
        self.location = location
        self.country_code = country_code
        self.timeout = timeout
        self.do_web_search = web_search
        self.do_yelp_search = yelp_search
        self.gmap_search = gmap_search

    async def web_search_ranking(
        self, bing_search: List[Link] | None, google_search: List[Link] | None
    ) -> dict:
        """
        This function takes the bing and google search results and returns a combined dictionary of all search links.
        """

        if not bing_search:
            log.warning(f"No Bing search results")
            return google_search
        elif not google_search:
            log.warning(f"No Google search results")
            return bing_search

        links = {}
        combined_results = []
        for results in zip_longest(google_search, bing_search):
            for i in range(2):
                if not isinstance(results[i], Link):
                    continue
                source = "Google" if i == 0 else "Bing"
                search_link = results[i].link
                if search_link in links.keys():
                    links[search_link].addSource(source)
                    continue

                links[search_link] = results[i]
                combined_results.append(results[i])

        return combined_results

    async def search_bing(
        self,
        search_query: str,
        bing_api_key: str = None,
        country: str = "US",
        site_limit: int = 10,
    ) -> List[dict] | None:
        """
        Search the web for the query using Google.\
        Uses Programmable Search Engine (CSE) API

        ### Parameters
        - search_query: The query to search for
        - bing_api_key: The Bing API key to use
        - country: The country to search in, default IN
        - site_limit: The number of sites to return

        langauge: en
        country: ['AU', 'CA', 'IN', 'FR', 'DE', 'JP', 'NZ', 'GB', 'US']

        ### Returns:
        - List[dict] or None: A list of dictionaries representing the search results. Each dictionary contains the following fields:
        - "index": The index of the result.
        - "title": The title of the web page.
        - "link": The URL of the web page.

        If the search is unsuccessful or encounters an error, None is returned.
        """

        if bing_api_key is None:
            try:
                bing_api_key = config.get_bing_search_api_key()
            except Exception as e:
                log.error(f"No Bing API key found")
                return None

        if country not in ["AU", "CA", "IN", "FR", "DE", "JP", "NZ", "GB", "US"]:
            log.error(f"Invalid country code, for Bing search")
            return None

        t_flag1 = time.time()

        api_endpoint = f"https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": bing_api_key}
        params = {
            "q": (search_query).replace(" ", "+"),
            "cc": country,
            "setLang": "en",
            "count": site_limit,
        }

        try:
            response = requests.get(
                api_endpoint, params=params, headers=headers, timeout=5
            )
            response.raise_for_status()
        except Exception as e:
            log.error(f"Error on Bing Search request: {e}")
            return None

        websites = []
        data = response.json()
        t_flag2 = time.time()
        log.debug(f"Bing search time for {search_query}: {t_flag2 - t_flag1}")

        if LOG_FILES:
            with open("src/log_data/bing.json", "w") as f:
                json.dump(data, f)

        if "error" not in data.keys() and "webPages" in data.keys():
            websites = [
                Link(
                    local_index=index,
                    title=result["name"],
                    link=result["url"],
                    query=search_query,
                    source=["Bing"],
                )
                for index, result in enumerate(data["webPages"]["value"])
            ]
        else:
            log.error(
                f"Bing search error: {data.get('error', {}).get('message', 'Unknown error')}"
            )
            return None

        return websites

    async def search_google(
        self,
        search_query: str,
        google_search_engine_id: str,
        google_api_key: str = None,
        country: str = "US",
        max_results: int = 10,
    ) -> List[dict] | None:
        """
        Search the web for the query using Google.\
        Uses Programmable Search Engine (CSE) API

        ### Parameters
        - search_query: The query to search for
        - google_search_engine_id: The Google Search Engine ID to use
        - google_api_key: The Google API key to use
        - country: The country to search in, default IN

        langauge: en
        country: ['AU', 'CA', 'IN', 'FR', 'DE', 'JP', 'NZ', 'UK', 'US']

        ### Returns:
        - List Object or None: A list of dictionaries representing the search results. Each dictionary contains the following fields:
        - "index": The index of the result.
        - "title": The title of the web page.
        - "link": The URL of the web page.
        - "query": Search Query

        If the search is unsuccessful or encounters an error, None is returned.
        """
        t_flag1 = time.time()

        if google_api_key is None:
            try:
                google_api_key = config.get_google_search_api_key()
            except Exception as e:
                log.error(f"No Google API key found")
                return None

        if google_search_engine_id is None:
            log.error(f"No Google Search Engine ID found")
            return None

        if country not in ["AU", "CA", "IN", "FR", "DE", "JP", "NZ", "UK", "US"]:
            log.error(f"Invalid country code, for Google search")
            return None
        
        if max_results > 10:
            log.warning(f"Google search max results limited to 10")
            max_results = 10

        api_endpoint = f"https://www.googleapis.com/customsearch/v1?key={google_api_key}&cx={google_search_engine_id}"

        params = {"q": search_query, "gl": country, "lr": "lang_en", "num": max_results}

        try:
            response = requests.get(api_endpoint, params=params, timeout=5)
            log.debug(f"Google search response code: {response.status_code}")
            response.raise_for_status()
        except Exception as e:
            log.error(f"Error on Google Search request: {e}")
            return None

        websites = []
        data = response.json()
        t_flag2 = time.time()
        log.debug(f"Google search time: {t_flag2 - t_flag1}")

        if "items" in data.keys() and "error" not in data.keys():
            websites = [
                Link(
                    local_index=index,
                    title=result["title"],
                    link=result["link"],
                    query=search_query,
                    source=["Google"],
                )
                for index, result in enumerate(data["items"])
            ]
        else:
            log.error(
                f"Google search error: {data.get('error', {}).get('message', 'Unknown error')}"
            )
            return None

        if LOG_FILES:
            with open("src/log_data/google.json", "w") as f:
                json.dump(data, f)

        return websites

    async def search_yelp(
        self,
        lat: int = None,
        lon: int = None,
        search_limit: int = 20,
        yelp_api_key: str = None,
    ):
        """
        Fetch results from Yelp API
        Yelp is used for fetching business data

        ### Parameters
        - lat: The latitude of the location
        - lon: The longitude of the location
        - search_limit: The number of results to return, default 10
        - yelp_api_key: The Yelp API key to use

        ### Returns:
        - List[dict] or None: A list of dictionaries representing the search results. Each dictionary contains the following fields:
        - "title": The title of the business.
        - "link": The URL of the business.
        - "emails": The emails of the business.
        - "mobileNumbers": The mobile numbers of the business.
        """
        yelp_url = "https://api.yelp.com/v3/businesses/search"

        if yelp_api_key is None:
            try:
                yelp_api_key = config.get_yelp_api_key()
            except Exception as e:
                log.error(f"No Yelp API key found")
                return None
        headers = {
            "Authorization": f"Bearer {yelp_api_key}",
            "accept": "application/json",
        }

        search_term = self.keyword
        location = self.location

        t_flag1 = time.time()
        params = {
            "term": search_term.replace(" ", "+"),
            "location": location.replace(" ", "+"),
            "limit": search_limit,
            "sort_by": "rating",
        }

        if lat and lon:
            params["latitude"] = lat
            params["longitude"] = lon

        data = {}

        try:
            response = requests.get(yelp_url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            t_flag2 = time.time()

            if LOG_FILES:
                with open("src/log_data/yelp.json", "w") as f:
                    json.dump(data, f)

            data = [
                {
                    "title": business["name"],
                    "link": business["url"],
                    "phone": business["phone"],
                    "location": business["location"]["display_address"],
                }
                for business in data["businesses"]
            ]
            log.info(
                f"Yelp search complete; {len(data)} results, time: {t_flag2 - t_flag1}"
            )

        except Exception as e:
            log.error(f"Error on Yelp Search request: {e}")
            return None

        return data

    def process_yelp_data(self, results: List[dict]):
        """
        Formats the results from Yelp API
        """
        processed_results = []
        for result in results:
            if result == None or isinstance(result, (Exception, str)) or result == []:
                continue
            if isinstance(result, dict):
                processed_result = {
                    "name": result["title"],
                    "source": result["link"],
                    "provider": ["Yelp"],
                    "contacts": {
                        "phone": [result["phone"]],
                        "email": [],
                        "address": ", ".join(result["location"]),
                    },
                }
                processed_results.append(processed_result)

        if LOG_FILES:
            with open("src/log_data/yelp_processed.json", "w") as f:
                json.dump(processed_results, f, indent=4)
        return processed_results

    def yelp_reverse_search(name: str, location: str, yelp_api_key: str = None):
        # TODO : need to intigrate with the above yelp search algorithm
        """
        Takes vendor's name, location to do a reverse search on yelp
        """

        yelp_url = "https://api.yelp.com/v3/businesses/search"

        if yelp_api_key is None:
            try:
                yelp_api_key = config.get_yelp_api_key()
            except Exception as e:
                log.error(f"No Yelp API key found")
                return None
        headers = {
            "Authorization": f"Bearer {yelp_api_key}",
            "accept": "application/json",
        }

        search_limit = 5

        t_flag1 = time.time()
        params = {
            "term": name.replace(" ", "+"),
            "location": location.replace(" ", "+"),
            "limit": search_limit,
            "sort_by": "best_match",
        }

        try:
            response = requests.get(yelp_url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            t_flag2 = time.time()

            if LOG_FILES:
                with open("src/log_data/yelp-r.json", "w") as f:
                    json.dump(data, f)

            data = [
                {
                    "title": business["name"],
                    "link": business["url"],
                    "phone": business["phone"],
                    "location": business["location"]["display_address"],
                    "rating": business["rating"],
                    "rating_count": business["review_count"],
                    "yelp_id": business["id"],
                    # "price": business['']
                    "latitude": business["coordinates"]["latitude"],
                    "longitude": business["coordinates"]["longitude"],
                }
                for business in data["businesses"]
            ]

            if len(data) == 0:
                return {}

            log.info(
                f"Yelp search complete; {len(data)} results, time: {t_flag2 - t_flag1}"
            )

            business_details = {}
            for business in data:
                if business["title"].lower().strip() == name.lower().strip():
                    business_details = business
                    break

            return business_details

        except Exception as e:
            log.error(f"Error on Yelp Search request: {e}")
            return None

    async def _search_google_business_details(self, place_id):
        """
        Search for the business details using Google Maps API, given the place_id
        """
        t_flag1 = time.time()
        URL = "https://maps.googleapis.com/maps/api/place/details/json"

        params = {
            "place_id": place_id,
            "fields": "name,formatted_address,formatted_phone_number,website",
            "key": config.get_google_maps_api_key(),
        }
        try:
            response = requests.get(URL, params=params)
            response.raise_for_status()
        except Exception as e:
            log.error(f"Error on Google Maps Search request: {e}")
            return None
        t_flag2 = time.time()
        log.info(
            f"Google Maps Business detail id: {place_id} search time: {t_flag2 - t_flag1}"
        )
        results = response.json()

        return results

    async def search_google_business(self):
        """
        Search for the business using Google Maps API
        """
        t_flag1 = time.time()
        log.info(f"\nStarting google maps search...")
        URL = "https://places.googleapis.com/v1/places:searchText"

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": config.get_google_maps_api_key(),
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.internationalPhoneNumber,places.websiteUri,places.shortFormattedAddress,places.nationalPhoneNumber,places.rating,places.userRatingCount,places.location",
        }
        data = {"textQuery": str(self.gmaps_query)}

        try:
            response = requests.post(URL, json=data, headers=headers)
            response.raise_for_status()
        except Exception as e:
            log.error(f"Error on Google Maps Search request: {e}")
            return None
        t_flag2 = time.time()
        results = response.json().get("places", [])

        if LOG_FILES:
            with open("src/log_data/google_maps.json", "w") as f:
                json.dump(results, f, indent=4)

        log.debug(f"Google Maps search results: {results}")
        log.info(
            f"\nGoogle Maps search Complete; {len(results)} items, time: {t_flag2 - t_flag1} !!\n"
        )

        return results

    def process_google_business_links(self, results: List[dict]) -> List[Link]:
        """ """
        processed_results = []
        for result in results:
            if (
                result == None
                or isinstance(result, (Exception, str))
                or result == []
                or "websiteUri" not in result.keys()
            ):
                continue
            if isinstance(result, dict):
                processed_results.append(
                    Link(
                        title=result["displayName"].get("text", ""),
                        link=result.get("websiteUri", ""),
                        source=["Google Maps"],
                        latitude=result["location"]["latitude"],
                        longitude=result["location"]["longitude"],
                        rating=str(result.get("rating", "-")),
                        rating_count=str(result.get("userRatingCount", "-")),
                    )
                )
        return processed_results

    # TODO : Refactor this function, not in use
    def process_google_business_results(self, results: List[dict]):
        """
        Formats the results from Google Maps API
        """
        processed_results = []
        for result in results:
            if result == None or isinstance(result, (Exception, str)) or result == []:
                continue
            if isinstance(result, dict):
                processed_result = {
                    "name": result["displayName"].get("text", ""),
                    "source": result.get("websiteUri", ""),
                    "provider": ["Google Maps"],
                    "contacts": {
                        "phone": [result.get("internationalPhoneNumber", "")],
                        "email": [],
                        "address": result.get("formattedAddress", ""),
                    },
                }
                # Link(
                #     title=result["displayName"].get("text", ""),
                #     link=result.get("websiteUri", ""),
                #     source=["Google Maps"],
                #     latitude=result["location"]["latitude"],
                #     longitude=result["location"]["longitude"],
                #     rating=str(result.get("rating", "-")),
                #     rating_count=str(result.get("userRatingCount", "-")),
                # )
                processed_results.append(processed_result)
        return processed_results

    async def single_web_search(self, query, location, max_results=20) -> List[dict]:
        """
        Parallely search the web using Google and Bing
        """
        log.info(f"Starting web search for : | {query} | in {location}")
        t_flag1 = time.time()
        tasks = [
            self.search_google(
                query, config.get_google_search_engine_id(), config.get_google_search_api_key(), self.country_code
            ),
            self.search_bing(query, config.get_bing_search_api_key(), self.country_code, site_limit=20),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        google_results, bing_results = results

        log.debug(
            f"Google search results for {query} : {getLinkJsonList(google_results)}"
        )
        log.debug(f"Bing search results for {query} : {getLinkJsonList(bing_results)}")

        # Merge the search results
        search_results = await self.web_search_ranking(bing_results, google_results)
        log.debug(f"Web search results: {getLinkJsonList(search_results)}")
        search_results = search_results[:max_results]

        t_flag2 = time.time()
        log.info(
            f"Web search for query: {query} completed in {t_flag2 - t_flag1} seconds\n"
        )
        return search_results

    def gen_search_results(self, search_results, max_results: int = 15):
        """
        Generate the search results
        """
        if len(search_results) == 0:
            return []
        if len(search_results) == 1:
            return search_results[0][:max_results]

        common_results = []
        total = 0
        i = 0

        for results in zip_longest(*search_results):
            for result in results:
                if not isinstance(result, Link):
                    continue
                if result.link not in [r.link for r in common_results]:
                    common_results.append(result)
                    total += 1
                if total >= max_results:
                    break
            if total >= max_results:
                break

        common_results = list(common_results[:max_results])
        log.info(f"Common search results ready!")

        # FIXME : Need to refactor this, dict to List
        if LOG_FILES:
            with open("src/log_data/common_search_results.json", "w") as f:
                json.dump(getLinkJsonList(common_results), f, indent=4)
        return common_results

    async def secondary_web_search(self, docs: List[Link]) -> List[Link]:
        """
        Takes primary search docs and does a secondary search on the web based in the vendor_name in metadata
        """
        log.info(f"Starting secondary web search")
        t_flag1 = time.time()
        search_jobs = []

        for doc in docs:
            vendor_name = doc.vendor_name
            if vendor_name:
                log.info(f"Vendor name search: {vendor_name}")
                search_query = (
                    f"{vendor_name} {self.location} contact email"
                    if len(self.location) > 2
                    else f"{vendor_name} contact email"
                )
                search_jobs.append(
                    self.search_google(
                        search_query, config.get_google_search_engine_id(), config.get_google_search_api_key(), self.country_code, max_results=2
                    )
                )

        search_results = await asyncio.gather(*search_jobs, return_exceptions=True)
        search_results = self.gen_search_results(search_results, max_results=20)

        t_flag2 = time.time()
        log.warning(
            f"\nSecondary Web search completed in {t_flag2 - t_flag1} seconds\n"
        )

        if LOG_FILES:
            with open("src/log_data/secondary_search_results.json", "w") as f:
                json.dump(getLinkJsonList(search_results), f, indent=4)
        return search_results

    async def search_web(self, max_results: int = 20, search_gmaps=False) -> List[Link]:
        """
        Parallely search multiple queries on the web
        """
        log.info(f"Starting multiple web search ")
        t_flag1 = time.time()
        search_jobs = []

        for query in self.web_queries:
            search_jobs.append(self.single_web_search(query, self.location))

        if search_gmaps and self.gmaps_query:
            search_jobs.append(self.search_google_business())

        search_results = await asyncio.gather(*search_jobs, return_exceptions=True)

        if search_gmaps and self.gmaps_query:
            gmaps_results = search_results[-1]
            if gmaps_results is not None:
                gmaps_links = self.process_google_business_links(gmaps_results)
                gmaps_links = gmaps_links[:25]
                search_results[-1] = gmaps_links

        log.debug(f"\n\nThe combined results: {getLinkJsonList(search_results)}\n")
        search_results = self.gen_search_results(search_results, max_results)

        t_flag2 = time.time()
        log.warning(f"\nComplete Web search completed in {t_flag2 - t_flag1} seconds\n")

        return search_results
