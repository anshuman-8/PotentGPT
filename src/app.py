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

load_dotenv()

SERP_ENV = os.getenv("SERP_API_AUTH")
OPENAI_ENV = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
BING_API_KEY = os.getenv("BING_API_KEY")
YELP_API_KEY = os.getenv("YELP_API_KEY")


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


async def web_probe(id: str, prompt: str, location: str, country_code: str):
    log.info(f"Prompt: {prompt}")
    goal_solution = ""
    # sanitize the prompt
    try:
        sanitized_prompt = sanitize_search_query(
            prompt, location=location, open_api_key=OPENAI_ENV
        )
        search_query = sanitized_prompt["search_query"]
        goal_solution = sanitized_prompt["solution"]
    except Exception as e:
        log.error(f"Prompt sanitization failed")
        raise Exception("Prompt sanitization failed")
        return HTTPException(
            status_code=500, detail={"id": id, "message": "Prompt sanitization failed"}
        )
    log.info(f"\nSanitized Prompt: {sanitized_prompt}\n")

    # search the web for the query
    search_client = Search(
        query=search_query, location=location, country_code=country_code, timeout=5
    )

    # get the search results
    search_results = await search_client.search_web()

    # process the search links
    refined_search_results = process_search_results(search_results[:14])
    log.info(f"\nRefined Search Results: {refined_search_results}\n")

    # scrape the websites
    extracted_content = await scrape_with_playwright(refined_search_results)
    log.info(f"\nScraped Content: {len(extracted_content)}\n")

    if len(extracted_content) == 0:
        log.error("No content extracted")
        raise Exception("No web content extracted!")
        return HTTPException(
            status_code=500, detail={"id": id, "message": "No web content extracted!"}
        )

    # Preprocess the extracted content
    context_data = process_data_docs(extracted_content, 400)
    log.info(f"\nContext Data len: {len(context_data)}\n")

    if len(context_data) == 0:
        log.error("No relevant data extracted")
        raise Exception("No relevant data extracted!")
        return HTTPException(
            status_code=500, detail={"id": id, "message": "No relevant data extracted!"}
        )
    return (context_data, goal_solution)


async def stream_contacts_retrieval(
    id: str, data, prompt: str, solution, context_chunk_size: int = 5
):
    """
    Extract the contacts from the search results using LLM
    """
    async for response in retrieval_multithreading(data, prompt, solution, OPENAI_ENV, context_chunk_size, max_thread=5, timeout=10):
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
        "response": results,
    }

    json_response = json.dumps(response).encode('utf-8', errors="replace")

    return json_response
