import time
import logging as log
from typing import List, Dict
from pydantic import BaseModel
from urllib.parse import urlparse


class ContactDetails(BaseModel):
    email: str = ""
    phone: str = ""
    address: str = ""


class ServiceProvider(BaseModel):
    id: int
    rank: int
    name: str
    target: str
    source: str
    info: str
    provider: List[str]
    latitude: float | None
    longitude: float | None
    rating: str
    rating_count: str
    contacts: ContactDetails


class YelpReverseSearchRequest(BaseModel):
    vendor: ServiceProvider
    location: str
    country_code: str


class ApiResponse(BaseModel):
    id: str
    prompt: str
    count: int
    location: str
    meta: dict
    results: List[ServiceProvider]


class CpAPIResponse(BaseModel):
    questions: List[dict]
    goal_type: str


class CpMergeRequest(BaseModel):
    goal: str
    choices: dict


class ErrorResponseModel(BaseModel):
    id: str
    prompt: str
    status: str = "error"
    message: str


class Feedback(BaseModel):
    id: str
    prompt: str
    message: str
    rating: int
    data: List[dict]


class Link:
    def __init__(
        self,
        title: str,
        link: str,
        source: List[str],
        query: str | None = None,
        local_index: int | None = None,
        base_url: str | None = None,
        latitude: str | None = None,
        longitude: str | None = None,
        rating: str | None = None,
        rating_count: str | None = None,
    ):
        self.id = None
        self.local_index = local_index
        self.rank = None
        self.title = title
        self.link = link
        self.query = query
        self.source = source
        self.base_url = base_url
        self.latitude = latitude
        self.longitude = longitude
        self.vendor_name = None
        self.rating = rating
        self.rating_count = rating_count
        self.address = None

    def __str__(self):
        return f"{self.title} - {self.link}"

    def getDomain(self):
        domain = urlparse(self.link).netloc
        return domain

    def addSource(self, source: str):
        if source not in self.source:
            self.source.append(source)

    def getDocumentMetadata(self):
        return {
            "id": self.id,
            "rank": self.rank,
            "title": self.title,
            "link": self.link,
            "source": self.source,
            "query": self.query,
            "local_index": self.local_index,
            "base_url": self.base_url,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "rating": self.rating,
            "rating_count": self.rating_count
        }

    def getJSON(self):
        return {
            "id": self.id,
            "rank": self.rank,
            "title": self.title,
            "link": self.link,
            "source": self.source,
            "meta": {
                "query": self.query,
                "local_index": self.local_index,
                "base_url": self.base_url,
                "latitude": self.latitude,
                "longitude": self.longitude,
                "rating": self.rating,
                "rating_count": self.rating_count,
            },
        }
    

def getLinkJsonList(links):
    """
    Convert the list or nested list of links to a list of JSON objects
    """
    link_list = []
    if not isinstance(links, (list, Link)):
        return link_list
    for link in links:
        if isinstance(link, list):
            link_list.extend(getLinkJsonList(link))
        else:
            if isinstance(link, Link):
                link_list.append(link.getJSON())
    return link_list


def check_duplicate_links(links: List[Link]) -> bool:
    """
    Check if there are duplicate links in the list of links
    """
    link_set = set()
    for link in links:
        if link.link in link_set:
            return True
        link_set.add(link.link)
    return False


class RequestContext:
    def __init__(self, id: str, prompt: str, location: str, country_code: str):
        self.id = id
        self.prompt = prompt
        self.location = location
        self.country_code = country_code or "US"
        self.start_time = time.time()
        self.isProduct = False

        self.contacts = []

        self.targets = []
        self.web_queries = None
        self.yelp_query = None
        self.gmaps_query = None

    def update_search_param(self, search_query: Dict[str, any], targets: List[str]):
        if (
            search_query is None
            or not isinstance(search_query, dict)
            or targets is None
            or not targets
        ):
            log.error(f"No search query or targets provided by Query Generator")
            raise Exception("Search query or Targets not passed")

        web_queries = search_query.get("web", None)
        if web_queries is None or not web_queries:
            log.error(f"No web search query provided")
            raise Exception("Web search query not passed")
        elif isinstance(web_queries, str) and web_queries.strip() == "":
            web_queries = [web_queries]

        yelp_query = search_query.get("yelp", None)
        if yelp_query is not None and yelp_query.strip() == "":
            yelp_query = None

        gmaps_query = search_query.get("gmaps", None)
        if gmaps_query is not None and gmaps_query.strip() == "":
            gmaps_query = None

        if isinstance(targets, str) and targets.strip() == "":
            targets = [targets]

        self.targets = targets
        self.web_queries = web_queries
        self.yelp_query = yelp_query
        self.gmaps_query = gmaps_query

    def add_contacts(self, contacts):
        self.contacts.extend(contacts)
