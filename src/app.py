import os
import json
import logging as log
from typing import List
from dotenv import load_dotenv
from fastapi import HTTPException

from src.sanitize_query import sanitize_search_query
from src.webScraper import scrape_with_playwright
from src.data_preprocessing import process_data_docs
from src.contactRetrieval import extract_contacts, retrieval_multithreading
from src.search import Search
from src.model import RequestContext
from src.utils import process_api_json

load_dotenv()

OPENAI_ENV = os.getenv("OPENAI_API_KEY")

def process_search_results(results: List[str]) -> List[str]:
    """
    Process the search links to remove the unwanted links
    """
    avoid_links = ["instagram", "facebook", "twitter", "youtube", "makemytrip", "linkedin", "justdial"]
    processed_results = []
    for result in results:
        if not any(avoid_link in result["link"] for avoid_link in avoid_links):
            processed_results.append(result)
    return processed_results


def search_query_extrapolate(request_context: RequestContext):
    log.info(f"Prompt: {request_context.prompt}")
    goal_solution = ""
    # sanitize the prompt
    try:
        sanitized_prompt = sanitize_search_query(
            request_context.prompt, location=request_context.location, open_api_key=OPENAI_ENV
        )
        search_query = sanitized_prompt["search_query"]
        goal_solution = sanitized_prompt["solution"]
        search_space  = list(sanitized_prompt["search"])
    except Exception as e:
        log.error(f"Prompt sanitization failed, Error:{e}")
        raise Exception("Prompt sanitization failed")
       
    log.info(f"\nSanitized Prompt: {sanitized_prompt}\n")
  
    return (search_query, goal_solution, search_space)


async def extract_web_context(request_context: RequestContext):
    """
    Extract the web context from the search results
    """
    search_client = Search(
        query=request_context.search_query, location=request_context.location, country_code=request_context.country_code, timeout=5, yelp_search=False
    )

    # get the search results
    web_results = await search_client.search_web()

    # process the search links
    refined_search_results = process_search_results(web_results[:15])
    log.info(f"\nRefined Search Results: {refined_search_results}\n")

    # scrape the websites
    extracted_content = await scrape_with_playwright(refined_search_results)
    log.info(f"\nScraped Content: {len(extracted_content)}\n")

    if len(extracted_content) == 0:
        log.error("No content extracted")
        raise Exception("No web content extracted!")

    # Preprocess the extracted content
    context_data = process_data_docs(extracted_content, 400)
    log.info(f"\nContext Data len: {len(context_data)}\n")

    if len(context_data) == 0:
        log.error("No relevant data extracted")
        raise Exception("No relevant data extracted!")
    return context_data



async def stream_contacts_retrieval(
    request_context: RequestContext, data, context_chunk_size: int = 5
):
    """
    Extract the contacts from the search results using LLM
    """
    if "gmaps" in request_context.search_space:
        search_client = Search(
            query=request_context.search_query, location=request_context.location, country_code=request_context.country_code, timeout=23
        )
        response = await search_client.search_google_business()
        details = search_client.process_google_business_results(response)
        log.info(f"\nGoogle Business Details: {details}\n")
        yield details
    
    async for response in retrieval_multithreading(data, request_context.prompt, request_context.solution, OPENAI_ENV, context_chunk_size, max_thread=5, timeout=10):
        yield response


async def response_formatter(id:str, time, prompt:str, location:str, results, status="running", has_more:bool=True):

    response = {
        "id": str(id),
        "time": int(time),
        "status": status,
        "has_more": has_more,
        "location": str(location),
        "prompt": str(prompt),
        "count": len(results),
        "results": results,
    }

    response = process_api_json(response)

    json_response = json.dumps(response).encode('utf-8', errors="replace")

    return json_response
