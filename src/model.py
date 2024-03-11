import time
import logging as log
from typing import List
from pydantic import BaseModel

class ContactDetails(BaseModel):
    email: str = ""
    phone: List[str] = []
    address: str = ""


class ServiceProvider(BaseModel):
    service_provider: str
    source: str
    provider: List[str]
    contacts: ContactDetails


class ApiResponse(BaseModel):
    id: str
    status: str
    prompt: str
    location: str
    country: str
    run_time: int
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
    id:str
    prompt:str
    message:str
    rating:int
    data: List[dict]



class RequestContext():
    def __init__(self, id:str, prompt:str, location:str, country_code:str, search_space:list=["web"]):
        self.id = id
        self.prompt = prompt
        self.location = location
        self.country_code = country_code or "US"
        self.start_time = time.time()

        self.contacts = []

        self.solution = None
        self.search_space = search_space
        self.keyword = None
        self.search_query = None

    def update_search_param(self, search_query:List[str], solution:str, keyword:str, search_space:list=["web"]):
        if search_query is None or not isinstance(search_query, list) or all(item == "" for item in search_query):
            log.error(f"No search query provided")
            raise Exception("Search query not passed")
        
        if solution is None or not solution.strip():
            log.error(f"No solution provided")
            raise Exception("Solution not passed")
        
        if keyword is None or not keyword.strip():
            log.error(f"No keyword provided")
            # raise Exception("Keyword not passed")
        
        if not search_space or all(item == "" for item in search_space) or not isinstance(search_space, list):
            log.error(f"No search space provided")
            raise Exception("Search space not passed")
        
        self.search_query = search_query
        self.solution = solution
        self.keyword = keyword
        self.search_space = search_space

    def add_contacts(self, contacts):
        self.contacts.extend(contacts)

