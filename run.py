
import os
import json
import time
import logging as log
from dotenv import load_dotenv
from openai import OpenAI
from typing import List, Dict
import asyncio

from src.webScraper import AsyncChromiumLoader
from src.webSearch import search_web_google, search_web_bing
from src.data_preprocessing import process_data_docs
from src.utils import create_documents, document_regex_sub, document2map
from src.search import Search

load_dotenv()


SERP_ENV = os.getenv("SERP_API_AUTH")
OPENAI_ENV = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
BING_API_KEY = os.getenv("BING_API_KEY")
YELP_API_KEY = os.getenv("YELP_API_KEY")

LOG_FILES = True

log.basicConfig(
    filename="logging.log",
    filemode="w",
    format="%(name)s - %(levelname)s - %(message)s",
    level=log.INFO,
)


def gpt_cost_calculator(
    inp_tokens: int, out_tokens: int, model: str = "gpt-3.5-turbo"
) -> int:
    """
    Calculate the cost of the GPT API call
    """
    cost = 0
    # GPT-3.5 Turbo
    if model == "gpt-3.5-turbo":
        input_cost = 0.0010
        output_cost = 0.0020
        cost = ((inp_tokens * input_cost) + (out_tokens * output_cost)) / 1000
    # GPT-4
    elif model == "gpt-4":
        input_cost = 0.03
        output_cost = 0.06
        cost = ((inp_tokens * input_cost) + (out_tokens * output_cost)) / 1000
    else:
        log.error("Invalid model")

    return cost


def scrape_with_playwright(results: List[str]) -> List[dict]:
    """
    Scrape the websites using playwright and chunk the text tokens
    """
    t_flag1 = time.time()
    loader = AsyncChromiumLoader(results)
    docs = loader.load_data()
    t_flag2 = time.time()

    if LOG_FILES:
        with open("src/log_data/docs.json", "w") as f:
            json.dump(document2map(docs), f)

    log.info(f"AsyncChromiumLoader time: { t_flag2 - t_flag1}")

    return docs


def process_search_results(results: List[str]) -> List[str]:
    """
    Process the search links to remove the unwanted links
    """
    avoid_links = ["instagram", "facebook", "twitter", "youtube", "makemytrip"]
    processed_results = []
    for result in results:
        if not any(avoid_link in result['link'] for avoid_link in avoid_links):
            processed_results.append(result)
    return processed_results


def sanitize_search_query(prompt: str, location: str = None) -> json:
    """
    Sanitize the search query using OpenAI for web search
    """
    t_flag1 = time.time()
    client = OpenAI(api_key=OPENAI_ENV)

    prompt = f"{prompt.strip()}"

    system_prompt = """Understand the goal and provide the best solution task, and a web search query for the solution for solving and helping the user achieve their goals. Include the location if needed. 
The solution should be based on the finding the best person or service to contact for helping or completing the user goal. 
The output should be in JSON format, also saying where to search in a list, an enum (web, yelp, gmaps), where web is used for all cases and yelp is used only for restaurants, home services, food, and other services and repairs. `gmaps` is Google Maps, who can retrieve info about businesses and services in a location."""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": f"{system_prompt}"},
                {
                    "role": "user",
                    "content": "Location: Kochi, Kerala;\nGoal: I want a good chef for my anniversary party for 50 people.",
                },
                {
                    "role": "system",
                    "content": '{"solution":"Search for all event chefs in Kochi Kerala, to email and call them", "search_query":"Event Chefs in Kochi, Kerala", "search":["web", "yelp"]}',
                },
                {
                    "role": "user",
                    "content": "Location: Oakland, CA;\nGoal: I want a SUV car for rent for 2 days, for a trip to Yosemite.",
                },
                {
                    "role": "system",
                    "content": '{"solution":"Search for all Car rental service in Oakland, CA, Who can give SUV", "search_query":"SUVs car rental in Oakland, CA", "search":["web", "gmaps"]}',
                },
                {
                    "role": "user",
                    "content": "Location: - ;\nGoal: I need an internship in UC Davis in molecular biology this summer.",
                },
                {
                    "role": "system",
                    "content": '{"solution": "Search for all UC Davis professors specializing in molecular biology research, to email them", "search_query":"Professors UC Davis molecular biology and internship contacts.", "search":["web"]}',
                },
                {"role": "user", "content": f"Location: {location};\nGoal: {prompt}"},
            ],
        )
    except Exception as e:
        log.error(f"Error in OpenAI query sanitation: {e}")
        exit(1)

    t_flag2 = time.time()
    log.info(f"OpenAI sanitation time: {t_flag2 - t_flag1}")

    # tokens used
    tokens_used = response.usage.total_tokens
    cost = gpt_cost_calculator(
        response.usage.prompt_tokens, response.usage.completion_tokens
    )
    log.info(f"Tokens used: {tokens_used}")
    log.info(f"Cost for search query sanitation: ${cost}")
    try:
        result = json.loads(response.choices[0].message.content)
    except Exception as e:
        log.error(f"Error parsing json: {e}")
        result = {}
    return result


def internet_speed_test():
    import speedtest

    s = speedtest.Speedtest()

    # Get the download speed
    download_speed = s.download()

    # Get the upload speed
    upload_speed = s.upload()

    print(f"Download speed: {(download_speed/(8 * 1024 * 1024)):6.3f} MB/s")
    print(f"Upload speed: {(upload_speed/(8 * 1024 * 1024)):5.3f} MB/s")


async def main():
    try:
        os.remove("src/output.txt")
    except Exception as e:
        pass

    location = "Oakland, CA"
    # prompt = input("\nEnter the search prompt: ").strip()
    prompt = "I want a good chef for my anniversary party for 50 people."
    # prompt = "I need an internship in UC Davis in molecular biology this summer."
    # prompt = "I want a car for rent for a week."
    log.info(f"\nPrompt: {prompt}\n")

    process_start_time = time.time()

    # sanitize the prompt
    sanitized_prompt = sanitize_search_query(prompt, location)
    log.info(f"\nSanitized Prompt: {sanitized_prompt}\n")
    if len(sanitized_prompt) == 0:
        log.error("Error in prompt sanitation")

    search_space = sanitized_prompt["search"]
    
    
    print(f"Sanitized Prompt: {sanitized_prompt}")
    search_client = Search(query=sanitized_prompt["search_query"],location=location, country_code="IN", timeout=23)
    data = search_client.search_yelp()
    data = search_client.process_yelp_data(data)
    print(f"Yelp Data: {data}")
    exit(0)
    response = await search_client.search_google_business()

    with open("src/log_data/maps.json", "w") as f:
            json.dump((response), f)

    processed_details = search_client.process_google_business_results(response)
    print(f"Extracted details: ${processed_details}")
    # search the web for the query
    google_search_results = search_web_google(
        sanitized_prompt["search_query"], GOOGLE_SEARCH_ENGINE_ID, GOOGLE_API_KEY, "IN"
    )
    bing_search_results = search_web_bing(
        sanitized_prompt["search_query"], BING_API_KEY
    )

    if google_search_results is not None:
        log.info(f"\ngoogle Search Results: {google_search_results}\n")
    if bing_search_results is not None:
        log.info(f"\nBing Search Results: {bing_search_results}\n")
    else:
        log.error("search failed")
        exit(1)

    # write both the search results to a same file
    with open("src/log_data/search_results.json", "w") as f:
        json.dump(google_search_results + bing_search_results, f)

    # merge the search results
    search_results = search_indexing(bing_search_results, google_search_results)

    # process the search links
    refined_search_results = process_search_results(search_results[:14])

    # scrape the websites
    extracted_content = scrape_with_playwright(refined_search_results)
    log.info(f"\nScraped Content: {len(extracted_content)}\n")

    if len(extracted_content) == 0:
        log.error("No content extracted")
        exit(1)

    # Preprocess the extracted content
    context_data = process_data_docs(extracted_content, 500)
    log.info(f"\nContext Data len: {len(context_data)}\n")

    if len(context_data) == 0:
        log.error("No relevant data extracted")
        exit(1)

    # extract the contacts from the search results
    extracted_contacts = llm_contacts_retrieval(context_data[:35], prompt, OPENAI_ENV)
    log.info(f"Extracted Contacts: {extracted_contacts}\n")

    process_end_time = time.time()
    log.info(f"\nTotal time: {process_end_time - process_start_time}")

    log.info(f"\nCompleted\n")
    exit(0)


if __name__ == "__main__":
    # main()
    asyncio.run(main())
    # internet_speed_test()
