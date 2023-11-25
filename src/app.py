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
from langchain.docstore.document import Document
from typing import List, Iterator

from webScraper import AsyncChromiumLoader
from tokenSplit import split_text_on_tokens_custom, Tokenizer
from documentUtils import create_documents, document_regex_sub, document2map

load_dotenv()

schema = {
    "properties": {
        "person_name": {"type": "string"},
        "service_provided": {"type": "string"},
        "service_location": {"type": "string"},
        "service_price": {"type": "string"},
        "contact email": {"type": "string"},
        "contact number": {"type": "string"},
    },
    "required": ["person_name", "news_article_summary"],
}

OPENAI_ENV = os.getenv("OPENAI_API_KEY")
SERP_ENV = os.getenv("SERP_API_AUTH")

log.basicConfig(
    filename="logging.log",
    filemode="w",
    format="%(name)s - %(levelname)s - %(message)s",
    level=log.DEBUG,
)


def scrape_with_playwright(urls: List[str]) -> List[dict]:
    """
    Scrape the websites using playwright and chunk the text tokens
    """
    t_flag1 = time.time()
    loader = AsyncChromiumLoader(urls)
    docs = loader.load()
    t_flag2 = time.time()
    log.info(f"AsyncChromiumLoader time: { t_flag2 - t_flag1}")

    bs_transformer = beautiful_soup_transformer.BeautifulSoupTransformer()
    docs_transformed = bs_transformer.transform_documents(
        docs, tags_to_extract=["p", "li", "div", "a", "span"]
    )
    # remove long white space
    docs_transformed = document_regex_sub(docs_transformed, r"\s+", " ")
    t_flag3 = time.time()
    log.info(f"BeautifulSoupTransformer time: {t_flag3 - t_flag2}")

    # first 400 tokens of the site
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=400, chunk_overlap=40
    )
    splits = splitter.split_documents(docs_transformed)

    t_flag4 = time.time()
    log.info(f"RecursiveCharacterTextSplitter time: {t_flag4 - t_flag3}")

    # convert to dictoinary
    splits = document2map(splits)

    with open("src/log_data/splits.json", "w") as f:
        json.dump(splits, f)

    log.info(f"Total data splits: {len(splits)}")
    return splits


def contains_contacts(text):
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

    with open("src/log_data/context_data.json", "w") as f:
        json.dump(data, f)

    return data


def extract_contacts(data, prompt):
    """
    Extract the contacts from the search results using LLM
    """
    t_flag1 = time.time()
    client = OpenAI(api_key=OPENAI_ENV)

    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant designed to extract insightful data helping the needs and output JSON. You take JSON as input and understand the schema and the content. The output format should be in [{'Service Provider': '...', 'contact' : {'email': '...', 'phone': '...', 'address': '...'}},{...}] here it is the list of all different service providers options with their contact details. If any of the fields are not present, you can leave them as empty strings.",
            },
            {"role": "user", "content": f"{data}"},
            {"role": "user", "content": f"{prompt}"},
        ],
    )
    t_flag2 = time.time()
    log.info(f"OpenAI time: { t_flag2 - t_flag1}")
    print(response.choices[0].message.content)

    with open("src/log_data/output.json", "w") as f:
        json.dump(response.choices[0].message.content, f)

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

    # write it to a file
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

    return response.choices[0].message.content


def main():
    process_start_time = time.time()

    prompt = input("Enter the search prompt: ").strip()
    log.info(f"\nPrompt: {prompt}\n")

    # # sanitize the prompt
    sanitized_prompt = sanitize_search_query(prompt)
    log.info(f"\nSanitized Prompt: {sanitized_prompt}\n")

    # # search the web for the query
    search_results = web_search(sanitized_prompt, "Kochi, Kerala")
    log.info(f"\nSearch Results: {search_results}\n")

    # list of websites
    websites = list(search_results.values())

    # scrape the websites
    extracted_content = scrape_with_playwright(websites)
    # log.info(f"\nExtracted Content: {extracted_content}\n")
    log.info(f"\nExtracted Content Length(chunked): {len(extracted_content)}\n")

    # extract relevant data from the search results
    context_data = relevant_data(extracted_content)
    log.info(f"\nContext Data: {context_data}\n")

    # extract the contacts from the search results
    extracted_contacts = extract_contacts(context_data, prompt)
    log.info(f"Extracted Contacts: {extracted_contacts}\n")

    process_end_time = time.time()
    log.info(f"\nTotal time: {process_end_time - process_start_time}")


if __name__ == "__main__":
    main()
