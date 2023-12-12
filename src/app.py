import re
import os
import json
import time
import logging as log
from dotenv import load_dotenv
from openai import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_transformers import beautiful_soup_transformer
from typing import List, Iterator, Dict
from langchain.docstore.document import Document

from webScraper import AsyncChromiumLoader
from search_indexing import search_indexing
from webSearch import search_web_google, search_web_bing
from tokenSplit import split_text_on_tokens_custom, Tokenizer
from documentUtils import create_documents, document_regex_sub, document2map

load_dotenv()


SERP_ENV = os.getenv("SERP_API_AUTH")
OPENAI_ENV = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
BING_API_KEY = os.getenv("BING_API_KEY")
YELP_API_KEY = os.getenv("YELP_API_KEY")

LOG_FILES = False

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


def scrape_with_playwright(urls: List[str]) -> List[dict]:
    """
    Scrape the websites using playwright and chunk the text tokens
    """
    t_flag1 = time.time()
    loader = AsyncChromiumLoader(urls)
    docs = loader.load_data()
    t_flag2 = time.time()

    if LOG_FILES:
        with open("src/log_data/docs.json", "w") as f:
            json.dump(document2map(docs), f)

    log.info(f"AsyncChromiumLoader time: { t_flag2 - t_flag1}")

    return docs


def preprocess_text(docs: Document, chunk_size: int = 400) -> Dict:
    """
    Preprocess the text using BeautifulSoup and chunk the text tokens
    """
    t_flag1 = time.time()

    # Beautiful Soup Transformer
    bs_transformer = beautiful_soup_transformer.BeautifulSoupTransformer()
    docs_transformed = bs_transformer.transform_documents(
        docs,
        tags_to_extract=["p", "li", "div", "a", "span"],
        unwanted_tags=["script", "style", "noscript", "svg"],
    )
    # remove long white space
    docs_transformed = document_regex_sub(docs_transformed, r"\s+", " ")
    docs_transformed = document_regex_sub(
        docs_transformed, r"javascript:void\(0\);", ""
    )
    docs_transformed = document_regex_sub(docs_transformed, r"\\u[0-9A-Fa-f]{4}", "")

    t_flag2 = time.time()
    log.info(f"BeautifulSoupTransformer time: {t_flag2 - t_flag1}")

    if LOG_FILES:
        with open("src/log_data/docs_beautify.json", "w") as f:
            json.dump(document2map(docs_transformed), f)

    # first N(chunk size) tokens of the site
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=chunk_size, chunk_overlap=40
    )
    splits = splitter.split_documents(docs_transformed)

    t_flag3 = time.time()
    log.info(f"RecursiveCharacterTextSplitter time: {t_flag3 - t_flag2}")

    # convert to dictoinary
    splits = document2map(splits)

    if LOG_FILES:
        with open("src/log_data/splits.json", "w") as f:
            json.dump(splits, f)

    log.info(f"Total data splits: {len(splits)}")
    return splits


def process_search_links(links: List[str]) -> List[str]:
    """
    Process the search links to remove the unwanted links
    """
    avoid_links = ["instagram", "facebook", "twitter", "youtube", "makemytrip"]
    processed_links = []
    for link in links:
        if not any(avoid_link in link for avoid_link in avoid_links):
            processed_links.append(link)
    return processed_links


def contains_contacts(text: str) -> bool:
    """
    Check if the text contains email or phone number
    """
    # Regular expression patterns for emails and phone numbers
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    # phone_pattern = r"\b(?:\+\d{1,2}\s?)?(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}\b"
    phone_pattern = r"\b(?:\+\d{1,3}\s?)?(?:\(\d{1,4}\)|\d{1,4})[\s.-]?\d{3,9}[\s.-]?\d{4}\b|\b\d{10}\b"

    contains_email = bool(re.search(email_pattern, text))
    contains_phone = bool(re.search(phone_pattern, text))

    return contains_email or contains_phone


def relevant_data(extracted_content):
    """
    Extract relevant data(checking for email and phone number) from the search results
    """
    t_flag1 = time.time()
    log.debug(f"before extraction: {len(extracted_content)}")
    data = [chunk for chunk in extracted_content if contains_contacts(chunk["content"])]
    log.debug(f"after extraction: {len(data)}")
    t_flag2 = time.time()
    log.info(f"Extraction time: {t_flag2 - t_flag1}")

    if LOG_FILES:
        with open("src/log_data/context_data.json", "w") as f:
            json.dump(data, f)

    return data


def extract_contacts(data, prompt: str) -> str:
    """
    Extract the contacts from the search results using LLM
    """
    # TODO: Take on max first 15 of the components of the data json

    t_flag1 = time.time()
    client = OpenAI(api_key=OPENAI_ENV)

    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": """Task: Efficiently extract contact details from JSON input, aiming to assist users question in finding service providers/vendors. Process complete Context data which contains content and its source in JSON format, comprehend its content, and provide a structured output with their respective contact details and descriptions. 
The response should strictly adhere to the format : ["Vendors": {"service_provider": "Name and description of the vendor", "source": "Source Link of the information", "contacts": {"email": "Email of the vendor","phone": "Phone number of the vendor","address": "Address of the vendor"}},].
Ensure that the output follows this template, and if any fields are absent in the input, leave them as empty as "". It is crucial not to omit any contact information. Do not Give Empty or Wrong Information.""",
            },
            {
                "role": "user",
                "content": f"Context: {data}\n\n---\n\nQuestion: {prompt}\n\nAnswer:All relevant and accurate contact details of the vendors in JSON:",
            },
        ],
    )
    t_flag2 = time.time()
    log.info(f"OpenAI time: { t_flag2 - t_flag1}")
    # print(response.choices[0].message.content)

    cost = gpt_cost_calculator(
        response.usage.prompt_tokens, response.usage.completion_tokens
    )
    log.debug(
        f"Input Tokens used: {response.usage.prompt_tokens}, Output Tokens used: {response.usage.completion_tokens}"
    )
    log.info(f"Cost for contact retrival: ${cost}")

    try:
        json_response = json.loads(response.choices[0].message.content)
    except Exception as e:
        log.error(f"Error parsing json: {e}")
        json_response = {}

    if LOG_FILES:
        with open("src/log_data/output.json", "w") as f:
            json.dump(json_response, f)

    return response.choices[0].message.content


def sanitize_search_query(prompt: str, location: str = None) -> json:
    """
    Sanitize the search query using OpenAI for web search
    """
    t_flag1 = time.time()
    client = OpenAI(api_key=OPENAI_ENV)

    prompt = f"{prompt.strip()}, {location}"

    system_prompt = "You are a helpful assistant designed to convert user input into a sanitized search query for web search (without adjectives) i.e. googling (with location). The output should be in JSON format also saying where to search in a list, enum (web, yelp), here web is used for all cases, yelp is used only for Restaurants, Home services, Auto service, and other service and repair."
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": f"{system_prompt}"},
                {
                    "role": "user",
                    "content": "I want a good chef for my anniversary party for 50 people, Kochi, Kerala",
                },
                {
                    "role": "system",
                    "content": '{"search_query":"Chefs in Kochi, Kerala", "search":["web", "yelp"]}',
                },
                {"role": "user", "content": f"{prompt}"},
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


def print_response(response_json):
    for vendor in response_json.get("Vendors", []):
        print(f"Service Provider: {vendor.get('service_provider', '')}")
        print(f"Source: {vendor.get('source', '')}")

        contacts = vendor.get("contacts", {})
        print(f"Contacts:")
        print(f"  Email: {contacts.get('email', '')}")
        print(f"  Phone: {contacts.get('phone', '')}")
        print(f"  Address: {contacts.get('address', '')}")

        print("\n" + "-" * 40 + "\n")


def internet_speed_test():
    import speedtest

    s = speedtest.Speedtest()

    # Get the download speed
    download_speed = s.download()

    # Get the upload speed
    upload_speed = s.upload()

    print(f"Download speed: {(download_speed/(8 * 1024 * 1024)):6.3f} MB/s")
    print(f"Upload speed: {(upload_speed/(8 * 1024 * 1024)):5.3f} MB/s")


def main():
    location = "Kochi, Kerala"
    prompt = input("\nEnter the search prompt: ").strip()
    log.info(f"\nPrompt: {prompt}\n")

    process_start_time = time.time()

    # sanitize the prompt
    sanitized_prompt = sanitize_search_query(prompt, location)
    log.info(f"\nSanitized Prompt: {sanitized_prompt}\n")

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

    # list of websites
    websites = [link["link"] for link in search_results]

    # process the search links
    refined_websites = process_search_links(
        websites[:14] if len(websites) > 14 else websites
    )

    # scrape the websites
    extracted_content = scrape_with_playwright(refined_websites)
    log.info(f"\nScraped Content: {len(extracted_content)}\n")

    if len(extracted_content) == 0:
        log.error("No content extracted")
        exit(1)

    # Preprocess the extracted content
    extracted_content = preprocess_text(extracted_content)
    log.info(f"\nPreprocessed Content Length(chunked): {len(extracted_content)}\n")

    # extract relevant data from the search results
    context_data = relevant_data(extracted_content)
    log.info(f"\nContext Data len: {len(context_data)}\n")

    if len(context_data) == 0:
        log.error("No relevant data extracted")
        exit(1)

    # extract the contacts from the search results
    extracted_contacts = extract_contacts(
        context_data[:12] if len(context_data) > 12 else context_data, prompt
    )
    log.info(f"Extracted Contacts: {extracted_contacts}\n")

    # print the response
    # print_response(json.loads(extracted_contacts))

    process_end_time = time.time()
    log.info(f"\nTotal time: {process_end_time - process_start_time}")

    log.info(f"\nCompleted\n")
    exit(0)


if __name__ == "__main__":
    main()
    # internet_speed_test()
