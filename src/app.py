import re
import os
import json
import time
import requests
import logging as log
from dotenv import load_dotenv
from openai import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_transformers import beautiful_soup_transformer
from typing import List, Iterator, Dict
from langchain.docstore.document import Document

from webScraper import AsyncChromiumLoader
from webSearch import search_web_google, serp_search
from tokenSplit import split_text_on_tokens_custom, Tokenizer
from documentUtils import create_documents, document_regex_sub, document2map

load_dotenv()


SERP_ENV = os.getenv("SERP_API_AUTH")
OPENAI_ENV = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

LOG_FILES = True

log.basicConfig(
    filename="logging.log",
    filemode="w",
    format="%(name)s - %(levelname)s - %(message)s",
    level=log.DEBUG,
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
    t_flag1 = time.time()

    # Beautiful Soup Transformer
    bs_transformer = beautiful_soup_transformer.BeautifulSoupTransformer()
    docs_transformed = bs_transformer.transform_documents(
        docs, tags_to_extract=["p", "li", "div", "a", "span"]
    )
    # remove long white space
    docs_transformed = document_regex_sub(docs_transformed, r"\s+", " ")
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


def contains_contacts(text: str) -> bool:
    """
    Check if the text contains email or phone number
    """
    # Regular expression patterns for emails and phone numbers
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    phone_pattern = r"\b(?:\+\d{1,2}\s?)?(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}\b"

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
                "content": 'Task: Efficiently extract contact details from JSON input, aiming to assist users question in finding service providers. Your task is to process Context data which contains content and its source in JSON format, comprehend its content, and provide a structured output. The desired answer format is a list of service providers with their respective contact details and descriptions. The response should strictly adhere to the format:["Vendors": {"service_provider": "Name and description of the vendor", "source": "Source Link of the information", "contact": {"email": "Email of the vendor","phone": "Phone number of the vendor","address": "Address of the vendor"}},]. Ensure that the output follows this template, and if any fields are absent in the input, leave them as empty. It is crucial not to omit any contact information.',
            },
            {
                "role": "user",
                "content": f"Context: {data}\n\n---\n\nQuestion: {prompt}\n\nAnswer:",
            },
        ],
    )
    t_flag2 = time.time()
    log.info(f"OpenAI time: { t_flag2 - t_flag1}")
    print(response.choices[0].message.content)

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


def web_search(search_query, location):
    """
    Search the web for the query using SERP API
    """
    t_flag1 = time.time()
    api_key = SERP_ENV
    api_endpoint = "https://serpapi.com/search"

    params = {"q": search_query, "location": location, "api_key": api_key}
    websites = {}

    response = requests.get(api_endpoint, params=params)
    data = response.json()
    t_flag2 = time.time()
    log.info(f"SERP time: {t_flag2 - t_flag1}")

    websites = {result["title"]: result["link"] for result in data["organic_results"]}

    if LOG_FILES:
        with open("src/log_data/websites.json", "w") as f:
            json.dump(websites, f)

    return websites


def sanitize_search_query(prompt):
    """
    Sanitize the search query using OpenAI for web search
    """
    t_flag1 = time.time()
    client = OpenAI(api_key=OPENAI_ENV)

    system_prompt = "You are a helpful assistant designed to convert a user input into a sanitized search query for web search i.e. googling. "

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": f"{system_prompt}"},
            {
                "role": "user",
                "content": "I want a good chef for my anniversary party in Kochi,Kerala for 50 people",
            },
            {"role": "system", "content": "Chefs in Kochi, Kerala"},
            {"role": "user", "content": f"{prompt}"},
        ],
    )
    t_flag2 = time.time()
    log.info(f"OpenAI sanitation time: {t_flag2 - t_flag1}")

    # tokens used
    tokens_used = response.usage.total_tokens
    cost = gpt_cost_calculator(
        response.usage.prompt_tokens, response.usage.completion_tokens
    )
    log.info(f"Tokens used: {tokens_used}")
    log.info(f"Cost for search query sanitation: ${cost}")

    return response.choices[0].message.content


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
    prompt = input("\nEnter the search prompt: ").strip()
    log.info(f"\nPrompt: {prompt}\n")

    process_start_time = time.time()

    # sanitize the prompt
    sanitized_prompt = sanitize_search_query(prompt)
    log.info(f"\nSanitized Prompt: {sanitized_prompt}\n")

    # search the web for the query
    search_results = search_web_google(
        sanitized_prompt, GOOGLE_SEARCH_ENGINE_ID, GOOGLE_API_KEY, "IN"
    )
    if search_results is not None:
        log.info(f"\nSearch Results: {search_results}\n")
    else:
        log.error("search failed")
        exit(1)

    # list of websites
    websites = [link["link"] for link in search_results]

    # scrape the websites
    extracted_content = scrape_with_playwright(websites)
    log.info(f"\nScraped Content: {len(extracted_content)}\n")

    # Preprocess the extracted content
    extracted_content = preprocess_text(extracted_content)
    log.info(f"\nPreprocessed Content Length(chunked): {len(extracted_content)}\n")

    # extract relevant data from the search results
    context_data = relevant_data(extracted_content)
    log.info(f"\nContext Data len: {len(context_data)}\n")

    # extract the contacts from the search results
    extracted_contacts = extract_contacts(context_data, prompt)
    log.info(f"Extracted Contacts: {extracted_contacts}\n")

    process_end_time = time.time()
    log.info(f"\nTotal time: {process_end_time - process_start_time}")

    log.info(f"\nCompleted\n")


if __name__ == "__main__":
    main()
    # internet_speed_test()
