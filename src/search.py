import os
import time
import json
import requests
import logging as log
import asyncio
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
GOOGLE_MAPS_KEY = os.getenv("GOOGLE_MAPS_KEY")
BING_API_KEY = os.getenv("BING_API_KEY")
YELP_API_KEY = os.getenv("YELP_API_KEY")


class Search:
    def __init__(
        self,
        query,
        location,
        country_code,
        timeout,
        web_search: bool = True,
        yelp_search: bool = True,
        google_business_search: bool = True,
    ):
        self.query = query
        self.location = location
        self.country_code = country_code
        self.timeout = timeout
        self.do_web_search = web_search
        self.do_yelp_search = yelp_search
        self.do_google_business_search = google_business_search


    async def web_search_ranking(self, bing_search:dict | None, google_search:dict | None)-> dict:
        """
        This function takes the bing and google search results and returns a combined dictionary of all search links.
        """
        if not bing_search:
            return google_search
        elif not google_search:
            return bing_search
        
        search_index = {}

        for results, source in zip([google_search, bing_search], ['google', 'bing']):
            for result in results:
                search_link = result['link']

                if search_link in search_index:
                    # Update the existing result with the new index
                    search_index[search_link]['index'].append(result['index'])
                    if source not in search_index[search_link]['source']:
                        search_index[search_link]['source'].append(source)
                else:
                    # Add a new entry to the merged results
                    search_index[search_link] = {
                        'index': [result['index']],
                        'title': result['title'],
                        'link': result['link'],
                        'displayLink': result['displayLink'],
                        'source': [source]
                    }

        final_result = list(search_index.values())

        # write to file
        with open('src/log_data/search_index.json', 'w') as f:
            json.dump(final_result, f, indent=4)

        return final_result

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
        - "displayLink": The display URL of the web page.

        If the search is unsuccessful or encounters an error, None is returned.
        """

        if bing_api_key is None:
            try:
                bing_api_key = os.getenv("BING_API_KEY")
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
        log.info(f"Bing search time: {t_flag2 - t_flag1}")

        # write it to a file
        with open("src/log_data/bing.json", "w") as f:
            json.dump(data, f)

        if "error" not in data.keys():
            websites = [
                {
                    "index": index,
                    "title": result["name"],
                    "link": result["url"],
                    "displayLink": result["displayUrl"],
                }
                for index, result in enumerate(data["webPages"]["value"])
            ]
        else:
            log.error(f"Bing search error: {data['error']['message']}")
            return None

        return websites


    async def search_google(
        self,
        search_query: str,
        google_search_engine_id: str,
        google_api_key: str = None,
        country: str = "US",
        site_limit: int = 10,
    ) -> List[dict] | None:
        """
        Search the web for the query using Google.\
        Uses Programmable Search Engine (CSE) API

        ### Parameters
        - search_query: The query to search for
        - google_search_engine_id: The Google Search Engine ID to use
        - google_api_key: The Google API key to use
        - country: The country to search in, default IN
        - site_limit: The number of sites to return, default 10

        langauge: en
        country: ['AU', 'CA', 'IN', 'FR', 'DE', 'JP', 'NZ', 'UK', 'US']

        ### Returns:
        - List[dict] or None: A list of dictionaries representing the search results. Each dictionary contains the following fields:
        - "index": The index of the result.
        - "title": The title of the web page.
        - "link": The URL of the web page.
        - "displayLink": The display URL of the web page.

        If the search is unsuccessful or encounters an error, None is returned.
        """
        t_flag1 = time.time()

        if google_api_key is None:
            try:
                google_api_key = os.getenv("GOOGLE_API_KEY")
            except Exception as e:
                log.error(f"No Google API key found")
                return None

        if google_search_engine_id is None:
            log.error(f"No Google Search Engine ID found")
            return None

        if country not in ["AU", "CA", "IN", "FR", "DE", "JP", "NZ", "UK", "US"]:
            log.error(f"Invalid country code, for Google search")
            return None

        api_endpoint = f"https://www.googleapis.com/customsearch/v1?key={google_api_key}&cx={google_search_engine_id}"

        params = {"q": search_query, "gl": country, "lr": "lang_en", "num": site_limit}

        try:
            response = requests.get(api_endpoint, params=params, timeout=5)
            log.info(f"Google search response code: {response.status_code}")
            response.raise_for_status()
        except Exception as e:
            log.error(f"Error on Google Search request: {e}")
            return None

        websites = []
        data = response.json()
        t_flag2 = time.time()
        log.info(f"Google search time: {t_flag2 - t_flag1}")

        if "error" not in data.keys():
            websites = [
                {
                    "index": index,
                    "title": result["title"],
                    "link": result["link"],
                    "displayLink": result["displayLink"],
                }
                for index, result in enumerate(data["items"])
            ]
        else:
            log.error(f"Google search error: {data['error']['message']}")
            return None
        
        return websites

    def search_yelp(
        self,
        search_term: str,
        location: str,
        lat: int = None,
        lon: int = None,
        search_limit: int = 10,
        yelp_api_key: str = None,
    ):
        """
        Fetch results from Yelp API
        Yelp is used for fetching business data

        ### Parameters
        - search_term: The search term to search for
        - location: The location to search in
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
        - "dataProvider": The data provider of the business.
        """
        yelp_url = "https://api.yelp.com/v3/businesses/search"

        if yelp_api_key is None:
            try:
                yelp_api_key = os.getenv("YELP_API_KEY")
            except Exception as e:
                log.error(f"No Yelp API key found")
                return None
        headers = {
            "Authorization": f"Bearer {yelp_api_key}",
            "accept": "application/json",
        }

        t_flag1 = time.time()
        params = {
            "term": search_term.replace(" ", "+"),
            "location": location.replace(" ", "+"),
            "limit": search_limit,
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
            print(f"Yelp search time: {t_flag2 - t_flag1}")

            print(data)
            data = [
                {
                    "title": business["name"],
                    "link": business["url"],
                    "phone": business["phone"],
                    "location": business["location"]["display_address"],
                }
                for business in data["businesses"]
            ]

            with open("./yelp.json", "w") as f:
                json.dump(data, f)

        except Exception as e:
            log.error(f"Error on Yelp Search request: {e}")
            return None

        return data

    async def _search_google_business_details(self, place_id):
        """
        """
        t_flag1 = time.time()
        URL = "https://maps.googleapis.com/maps/api/place/details/json"

        params = {
            'place_id': place_id,
            'fields': 'name,formatted_address,formatted_phone_number,website',
            'key': GOOGLE_MAPS_KEY,
        }
        try:
            response = requests.get(URL, params=params)
            response.raise_for_status()
        except Exception as e:
            log.error(f"Error on Google Maps Search request: {e}")
            return None
        t_flag2 = time.time()
        log.info(f"Google Maps Business detail id: {place_id} search time: {t_flag2 - t_flag1}")
        results = response.json()

        return results

    async def search_google_business(self):
        """

        """
        t_flag1= time.time()
        log.info(f"Starting google maps search")
        URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"

        params = {
            'query': self.query,
            'radius':5000,
            'key': GOOGLE_MAPS_KEY,
        }
        try:
            response = requests.get(URL, params=params)
            response.raise_for_status()
        except Exception as e:
            log.error(f"Error on Google Maps Search request: {e}")
            return None
        t_flag2 = time.time()
        log.debug(f"Google Maps search results: {response.json()}")
        log.info(f"Google Maps search time: {t_flag2 - t_flag1}")
        results = response.json().get('results', [])

        return results

    async def google_business_details(self, place_ids: List[str]):
        """
        Async function to fetch the details of the business from Google Maps
        """
        log.info(f"Starting Google Maps Details search for {place_ids}")
        t_start = time.time()
        tasks = [self._search_google_business_details(place_id) for place_id in place_ids]
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            log.error(f"Error in gathering tasks: {e}")
            results = []

        t_end = time.time()
        log.info(f"Google Maps Details search completed in {t_end - t_start} seconds")
        return results
    
    def process_google_business_results(self, results: List[dict]):
        """
        Formats the results from Google Maps API
        """
        processed_results = []
        for result in results:
            if result == None or isinstance(result, (Exception, str)) or result == []:
                continue
            if isinstance(result, dict) and 'result' in result:
                result = result['result']
                processed_result = {
                    'name': result.get('name', ''),
                    'source': result.get('website', ''),
                    'provider': ['Google Maps'],
                    'contacts': {
                        'phone': [result.get('formatted_phone_number', '')],
                        'email': [],
                        'address': result.get('formatted_address', '')
                    }
                }
                processed_results.append(processed_result)
        return processed_results
        

    async def search_web(self):
        """
        Parallely search the web using Google and Bing
        """
        log.warning(f"Starting web search for {self.query} in {self.location}")
        t_flag1 = time.time()
        tasks = [
            self.search_google(
                self.query, GOOGLE_SEARCH_ENGINE_ID, GOOGLE_API_KEY, self.country_code
            ),
            self.search_bing(self.query, BING_API_KEY, self.country_code),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        google_results, bing_results = results
        
        log.info(f"Google search results: {google_results}")
        log.info(f"Bing search results: {bing_results}")

        # Merge the search results
        search_results = await self.web_search_ranking(bing_results, google_results)
        log.info(f"Web search results: {search_results}")


        t_flag2 = time.time()
        log.warning(f"Web search completed in {t_flag2 - t_flag1} seconds")

        return search_results

    async def search(self):
        web_results = []
        yelp_results = []
        google_business_results = []

        if self.do_web_search:
            web_results = await self.search_web()
        if self.do_yelp_search:
            yelp_results = self.search_yelp(self.query, self.location)
        if self.do_google_business_search:
            google_business_results = self.search_google_business()

        return web_results, yelp_results, google_business_results
