import os
import json
import time
import logging as log
from typing import List
from dotenv import load_dotenv
from fastapi import HTTPException

from src.webSearch import search_web_google, search_web_bing
from src.sanitize_query import sanitize_search_query
from src.search_indexing import search_indexing
from src.webScraper import scrape_with_playwright
from src.data_preprocessing import process_data_docs
from src.contactRetrieval import llm_contacts_retrieval, extract_contacts

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
    avoid_links = ["instagram", "facebook", "twitter", "youtube", "makemytrip"]
    processed_results = []
    for result in results:
        if not any(avoid_link in result["link"] for avoid_link in avoid_links):
            processed_results.append(result)
    return processed_results


async def web_probe(id: str, prompt: str, location: str, country_code: str):
    log.info(f"Prompt: {prompt}")
    start_time = time.time()
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
    google_search_results = search_web_google(
        search_query,
        GOOGLE_SEARCH_ENGINE_ID,
        GOOGLE_API_KEY,
        country_code,
    )
    bing_search_results = search_web_bing(
        search_query, BING_API_KEY, country_code
    )

    if google_search_results is not None:
        log.info(f"\ngoogle Search Results: {google_search_results}\n")
    if bing_search_results is not None:
        log.info(f"\nBing Search Results: {bing_search_results}\n")
    else:
        log.error("search failed")
        raise Exception("Web search failed!")
        return HTTPException(
            status_code=500, detail={"id": id, "message": "Web search failed!"}
        )

    # merge the search results
    search_results = search_indexing(bing_search_results, google_search_results)

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
    context_data = process_data_docs(extracted_content, 500)
    log.info(f"\nContext Data len: {len(context_data)}\n")

    if len(context_data) == 0:
        log.error("No relevant data extracted")
        raise Exception("No relevant data extracted!")
        return HTTPException(
            status_code=500, detail={"id": id, "message": "No relevant data extracted!"}
        )

    # extract contacts
    extracted_contacts = extract_contacts(
        context_data[:15] if len(context_data) > 15 else context_data,
        prompt,
        goal_solution,
        OPENAI_ENV,
    )
    log.info(f"Extracted Contacts: {extracted_contacts}\n")

    time_taken = time.time() - start_time
    log.info(f"Time taken: {time_taken}")

    res = response_formatter(id, time_taken, prompt, location, extracted_contacts)

    return res


async def contacts_retrieval(id: str, context_data, prompt: str):
    """
    Extract the contacts from the search results using LLM
    """
    async for response in llm_contacts_retrieval( 
        id, context_data, prompt, open_ai_key=OPENAI_ENV
    ):
        # contacts.append(response)
        yield response_formatter(id, 12, prompt, "", response)
    # return contacts


def response_formatter(id, time, prompt, location, results):
    response = {
        "id": str(id),
        "time": int(time),
        "status": "complete",
        "location": str(location),
        "prompt": str(prompt),
        "count": len(results["results"]),
        "response": results["results"],
    }

    return response
