from langchain.docstore.document import Document
import logging as log
import json
import random
from typing import List, Optional
import copy
import re


def create_documents(
    texts: List[str], metadatas: Optional[List[dict]] = None
) -> List[Document]:
    """Create documents from a list of texts."""
    _metadatas = metadatas or [{}] * len(texts)
    documents = []
    for i, text in enumerate(texts):
        metadata = copy.deepcopy(_metadatas[i])
        new_doc = Document(page_content=text, metadata=metadata)
        documents.append(new_doc)
    return documents


def document_regex_sub(
    documents: List[Document], pattern: str, repl: str
) -> List[Document]:
    """Filter documents based on a regex pattern.
    ### Parameters:
    - documents: List of documents to be filtered.
    - pattern: Regex pattern to be matched.
    - repl: String to replace the matched pattern with.

    ### Returns:
    List of documents with the regex pattern replaced by the repl string.
    """
    texts, metadatas = [], []
    for doc in documents:
        texts.append(doc.page_content)
        metadatas.append(doc.metadata)
    texts = [re.sub(pattern, repl, text) for text in texts]
    return create_documents(texts, metadatas=metadatas)


def document2map(documents: List[Document]) -> List[dict]:
    """Convert a list of documents to a map."""
    log.info("Converting documents to map...")
    return [
        {"metadata": doc.metadata, "content": doc.page_content} for doc in documents
    ]

def rank_weblinks(web_links: List[dict]) -> List[dict]:
    """
    Ranks the web links by adding rank field and making the list unique
    """
    # make the list unique
    unique_web_links = []
    for web_link in web_links:
        if web_link not in unique_web_links:
            unique_web_links.append(web_link)

    # add rank field
    for i, web_link in enumerate(unique_web_links):
        web_link["rank"] = i + 1
        web_link["id"] = i 

    return unique_web_links

def inflating_retrieval_results(results: List[dict], base_informationList: List[dict]) -> List[dict]:
    """
    Inflating the retrieval results with the base information
    """
    inflated_results = []
    for result in results:
        id = result.get("id")
        if id is None:
            continue
        base_information = [info for info in base_informationList if info.get("metadata", {}).get("id") == id]
        if base_information[0] is None or base_information == []:
            continue
        base_information = base_information[0]
        base_information.pop("content", None)
        base_information["metadata"].pop("title", None)
        base_information["metadata"].pop("id", None)
        result = {**result, **base_information}
        inflated_results.append(result)

    return inflated_results

def sort_results(results: List[dict]) -> List[dict]:
    """
    Sort the results based on the rank
    """
    sorted_list = sorted(results, key=lambda x: x['rank'])

    results = []
    # Reassign the ranks as 1, 2, 3, ...
    for index, item in enumerate(sorted_list, start=1):
        updated_item = dict(item)
        updated_item['rank'] = index
        results.append(updated_item)

    return results


def process_api_json(response):
    """
    Process the API response
    """
    log.info(f"Processing API response : {response}")
    # Initialize an empty list to store processed results
    processed_results = []

    try:
        # Iterate over each result in the input data
        for result in response.get("results", []):
            if isinstance(result, str):
                try:
                    result = json.loads(result)  # Assuming result is a JSON string
                except json.JSONDecodeError:
                    result = {}
                    continue

            # Extract contacts and initialize empty lists for email and phone
            contacts = result.get("contacts", {})
            emails = []
            phones = []

            # Process emails using regex to extract valid formats
            if contacts.get("email"):
                if isinstance(contacts["email"], list):
                    emails = re.findall(
                        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                        ", ".join(contacts["email"]),
                    )
                else:
                    emails = re.findall(
                        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                        contacts["email"],
                    )

            # Process phone numbers using regex to extract valid formats
            if contacts.get("phone"):
                if isinstance(contacts["phone"], list):
                    phones = re.findall(
                        r"\b(?:\+\d{1,3}\s?)?(?:\(\d{1,4}\)|\d{1,4})[\s.-]?\d{3,9}[\s.-]?\d{4}\b|\b\d{10}\b",
                        ", ".join(contacts["phone"]),
                    )
                else:
                    phones = re.findall(
                        r"\b(?:\+\d{1,3}\s?)?(?:\(\d{1,4}\)|\d{1,4})[\s.-]?\d{3,9}[\s.-]?\d{4}\b|\b\d{10}\b",
                        contacts["phone"],
                    )

            # Create a new processed result dictionary
            processed_result = {
                "name": result.get("name", ""),
                "source": result.get("source", ""),
                "provider": result.get("provider", []),
                "contacts": {
                    "email": emails if emails else [],
                    "phone": phones if phones else [],
                    "address": contacts.get("address", ""),
                },
            }

            if (
                processed_result["contacts"]["email"] == []
                and processed_result["contacts"]["phone"] == []
                and processed_result["contacts"]["address"].strip() == ""
            ):
                continue

            # Append the processed result to the list
            processed_results.append(processed_result)

        # Create the processed JSON response
        processed_json = {
            "id": response.get("id", ""),
            "has_more": response.get("has_more", False),
            "prompt": response.get("prompt", ""),
            "location": response.get("location", ""),
            "time": response.get("time", 0),
            "count": len(processed_results),
            "results": processed_results,
        }
    except Exception as e:
        log.error(f"Error processing API response : {e}")
        raise Exception("Error processing API response")

    return processed_json

def process_results(results):
    log.info(f"Processing API results : {results}")
    # Initialize an empty list to store processed results
    processed_results = []

    try:
        for result in results:
            if isinstance(result, str):
                    try:
                        result = json.loads(result)
                    except json.JSONDecodeError:
                        result = {}

            contacts = result.get("contacts", {})
            email = ""
            phone = ""
            if contacts.get("email"):
                if isinstance(contacts["email"], list):
                    email = re.search(
                        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                        contacts["email"][0],
                    )
                else:
                    email = re.search(
                        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                        contacts["email"],
                    )

            if contacts.get("phone"):
                if isinstance(contacts["phone"], list):
                    phone = re.search(
                        r'\b(?:\+\d{1,3}\s?)?(?:\(\d{1,4}\)|\d{1,4})[\s.-]?\d{3,9}[\s.-]?\d{4}\b',
                        contacts["phone"][0],
                    )
                else:
                    phone = re.search(
                        r'\b(?:\+\d{1,3}\s?)?(?:\(\d{1,4}\)|\d{1,4})[\s.-]?\d{3,9}[\s.-]?\d{4}\b',
                        contacts["phone"],
                    )

            processed_result = {
                "id": result.get("id", random.randint(30, 60)),
                "rank": result.get("metadata",{}).get("rank"),
                "name": result.get("name", ""),
                "source": result.get("metadata",{}).get("link", ""),
                "info": result.get("info",""),
                "provider": result.get("metadata",{}).get("source", []),
                "latitude": result.get("metadata",{}).get("latitude", None),
                "longitude": result.get("metadata",{}).get("longitude", None),
                "rating": result.get("metadata",{}).get("rating", ""),
                "rating_count": result.get("metadata",{}).get("rating_count", ""),
                "contacts": {
                    "email": email.string if email else "",
                    "phone": phone.string if phone else "",
                    "address": contacts.get("address", ""),
                },
            }
            if (
                processed_result["contacts"]["email"].strip() == ""
                and processed_result["contacts"]["phone"].strip() == ""
                and processed_result["contacts"]["address"].strip() == ""
            ):
                continue

            # Append the processed result to the list
            processed_results.append(processed_result)
        
        # sorting
        processed_results = sort_results(processed_results)

    except Exception as e:
        log.error(f"Error processing API results : {e}")
        raise Exception("Error processing API results")
    
    return processed_results


def merge_response(car_rental_list):
    merged_services = {}

    for service in car_rental_list:
        phone = (
            service["contacts"]["phone"][0] if service["contacts"]["phone"] else None
        )
        name = service["name"]
        provider = service["provider"][0] if service["provider"] else None

        if phone not in merged_services:
            merged_services[phone] = {
                "name": name,
                "source": service["source"],
                "provider": [provider] if provider else [],
            }
        else:
            if provider and provider not in merged_services[phone]["provider"]:
                merged_services[phone]["provider"].append(provider)

    # Convert merged_services dictionary back to list of dictionaries
    merged_list = [
        {
            "name": value["name"],
            "source": value["source"],
            "provider": value["provider"],
            "contacts": {
                "phone": [phone],
                "email": [],  # You can add email merging logic if needed
                "address": "",  # You can add address merging logic if needed
            },
        }
        for phone, value in merged_services.items()
    ]

    return merged_list
