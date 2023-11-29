import os
import time
import json
import requests
import logging as log
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()


def serp_search(
    search_query: str, location: str, serp_api_key: str = None, site_limit: int = 10
) -> List[dict]:
    """
    Search the web for the query using SERP API

    ### Returns:
    List of {
        title: <title>,
        link: <link>
    }
    """
    t_flag1 = time.time()

    if serp_api_key is None:
        try:
            api_key = os.getenv("SERP_API_AUTH")
        except Exception as e:
            log.error(f"No Serp API key found")
            exit(1)

    api_endpoint = "https://serpapi.com/search"

    params = {"q": search_query, "location": location, "api_key": api_key}
    websites = {}

    response = requests.get(api_endpoint, params=params)
    data = response.json()
    t_flag2 = time.time()
    log.info(f"SERP search time: {t_flag2 - t_flag1}")

    data["organic_results"] = data["organic_results"][:site_limit]

    websites = [
        {"title": result["title"], "link": result["link"]}
        for result in data["organic_results"]
    ]

    return websites


def search_web_google(
    search_query: str,
    google_search_engine_id: str,
    google_api_key: str = None,
    country: str = "IN",
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
    response = requests.get(api_endpoint, params=params)

    websites = {}
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


def search_web_bing(
    search_query: str,
    bing_api_key: str = None,
    country: str = "IN",
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
        response = requests.get(api_endpoint, params=params, headers=headers)
    except Exception as e:
        log.error(f"Error on Bing Search request: {e}")
        return None

    websites = {}
    data = response.json()
    t_flag2 = time.time()
    log.info(f"Bing search time: {t_flag2 - t_flag1}")

    # write it to a file
    with open("./bing.json", "w") as f:
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


# prompt = "need a car for rent in kochi"
# ans = search_web_bing(prompt)

# print(ans)
