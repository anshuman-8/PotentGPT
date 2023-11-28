import time
import logging as log
import requests
import os
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
    location: str,
    google_search_engine_id: str,
    google_api_key: str = None,
    site_limit: int = 10,
) -> List[dict]:
    """
    Search the web for the query using Google.\
    Uses Programmable Search Engine (CSE) API

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

    api_endpoint = f"https://www.googleapis.com/customsearch/v1?key={google_api_key}&cx={google_search_engine_id}"

    params = {"q": search_query, "gl": location, "lr": "lang_en", "num": site_limit}
    response = requests.get(api_endpoint, params=params)

    websites = {}
    data = response.json()
    t_flag2 = time.time()
    log.info(f"Google search time: {t_flag2 - t_flag1}")

    if 'error' not in data.keys():
        websites = [
            {"title": result["title"], "link": result["link"]} for result in data['items']
        ]
    else:
        log.error(f"Google search error: {data['error']['message']}")
        return []

    return websites
