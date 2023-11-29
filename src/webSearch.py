import time
import logging as log
import requests
import os
import json
from typing import Dict, List
from dotenv import load_dotenv
from langchain.utilities import BingSearchAPIWrapper

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
    site_limit: int = 10,
    country: str = "IN",
) -> List[dict]:
    """
    Search the web for the query using Google.\
    Uses Programmable Search Engine (CSE) API

    ### Parameters
    - search_query: The query to search for
    - google_search_engine_id: The Google Search Engine ID to use
    - google_api_key: The Google API key to use
    - site_limit: The number of sites to return, default 10
    - country: The country to search in, default IN

    langauge: en
    country: ['AU', 'CA', 'IN', 'FR', 'DE', 'JP', 'NZ', 'UK', 'US']

    ### Returns:
    List of {
        title: <title>,
        link: <link>
    }
    """
    t_flag1 = time.time()

    if google_api_key is None:
        try:
            google_api_key = os.getenv("GOOGLE_API_KEY")
        except Exception as e:
            log.error(f"No Google API key found")
            exit(1)

    if google_search_engine_id is None:
        log.error(f"No Google Search Engine ID found")
        exit(1)

    if country not in ["AU", "CA", "IN", "FR", "DE", "JP", "NZ", "UK", "US"]:
        log.error(f"Invalid country code, for Google search")
        exit(1)

    api_endpoint = f"https://www.googleapis.com/customsearch/v1?key={google_api_key}&cx={google_search_engine_id}"

    params = {"q": search_query, "gl": country, "lr": "lang_en", "num": site_limit}
    response = requests.get(api_endpoint, params=params)

    websites = {}
    data = response.json()
    t_flag2 = time.time()
    log.info(f"Google search time: {t_flag2 - t_flag1}")

    if "error" not in data.keys():
        websites = [
            {"title": result["title"], "link": result["link"]}
            for result in data["items"]
        ]
    else:
        log.error(f"Google search error: {data['error']['message']}")
        return []

    return websites


def search_web_bing(
    search_query: str,
    bing_api_key: str = None,
    site_limit: int = 10,
    country: str = "IN",
) -> List[dict]:
    """
    Search the web for the query using Google.\
    Uses Programmable Search Engine (CSE) API

    ### Parameters
    - search_query: The query to search for
    - bing_api_key: The Bing API key to use
    - site_limit: The number of sites to return
    - country: The country to search in, default IN

    langauge: en
    country: ['AU', 'CA', 'IN', 'FR', 'DE', 'JP', 'NZ', 'GB', 'US']

    ### Returns:
    List of {
        title: <title>,
        link: <link>
    }
    """

    if bing_api_key is None:
        try:
            bing_api_key = os.getenv("BING_API_KEY")
        except Exception as e:
            log.error(f"No Bing API key found")
            exit(1)

    if country not in ["AU", "CA", "IN", "FR", "DE", "JP", "NZ", "GB", "US"]:
        log.error(f"Invalid country code, for Bing search")
        exit(1)

    t_flag1 = time.time()

    api_endpoint = f"https://api.bing.microsoft.com/v7.0/search"
    headers = {"Ocp-Apim-Subscription-Key": bing_api_key}
    params = {"q": (search_query).replace(" ", "+"), "cc": country, "setLang": "en", "count": site_limit}

    response = requests.get(api_endpoint, params=params, headers=headers)

    websites = {}
    data = response.json()
    t_flag2 = time.time()
    log.info(f"Bing search time: {t_flag2 - t_flag1}")

    if "error" not in data.keys():
        websites = [
            {"title": result["name"], "link": result["url"]}
            for result in data["webPages"]["value"]
        ]
    else:
        log.error(f"Bing search error: {data['error']['message']}")
        return []

    return websites


prompt = "need a car for rent in kochi"
ans = search_web_bing(prompt)

print(ans)

