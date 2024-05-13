import json
import re
import time
import logging as log
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, NavigableString, Tag
from typing import Dict, Any, Iterator, List, Sequence, cast, Tuple
from langchain.docstore.document import Document
from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain.text_splitter import RecursiveCharacterTextSplitter
from src.model import Link
from src.utils import create_documents, document_lambda, document2map


LOG_FILES = False


def transform_documents(
    doc: str,
    source_link: Link,
    unwanted_tags: List[str] = ["script", "style"],
    tags_to_extract: List[str] = ["p", "li", "div", "a"],
    remove_lines: bool = True,
) -> Tuple[List[Document], List[Link]]:
    site_contact_links = []
    # for doc in documents:
    # _content = doc.page_content
    cleaned_content, contact_href = tags_cleaning(doc, unwanted_tags, tags_to_extract)

    site_contact_link = combine_secondary_link(source_link, contact_href)

    if site_contact_link:
        site_contact_links.extend(site_contact_link)

    if remove_lines:
        cleaned_content = remove_unnecessary_lines(cleaned_content)

    # doc.page_content = cleaned_content

    return cleaned_content, site_contact_links


def combine_secondary_link(
    base_link: Link, contact_links: List[str]
) -> List[Link] | None:
    if len(contact_links) < 1:
        return None
    combined_links = []
    links = set()
    try:
        for single_contact_link in contact_links:
            combined_link = Link(
                title=base_link.title,
                link=base_link.link,
                source=base_link.source,
                query=base_link.query,
                latitude=base_link.latitude,
                longitude=base_link.longitude,
                rating=base_link.rating,
                rating_count=base_link.rating_count,
                base_link=base_link.link,
            )
            if (
                single_contact_link.startswith("href")
                and single_contact_link not in links
            ):
                combined_link.link = single_contact_link
                combined_links.append(combined_link)
                links.add(single_contact_link)
            else:
                base_domain = base_link.link
                combined_url = urljoin(base_domain, single_contact_link)
                if combined_url not in links:
                    combined_link.link = combined_url
                    combined_links.append(combined_link)
                    links.add(combined_link)

        return combined_links
    except Exception as e:
        log.warn(f"Error combining link: {e}")
        return None


# TODO : Remove it
def remove_unwanted_tags(html_content, unwanted_tags: List[str]) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in unwanted_tags:
        for element in soup.find_all(tag):
            element.decompose()
    return soup


def tags_cleaning(
    html_content,
    unwanted_tags: List[str] = ["script", "style"],
    tags_to_extract: List[str] = ["p", "li", "div", "a"],
) -> str:

    try:
        soup = BeautifulSoup(html_content, "html.parser")
        text_parts: List[str] = []
        contact_hrefs: List[str] = []
        for tag in unwanted_tags:
            for element in soup.find_all(tag):
                element.decompose()
        for element in soup.find_all(tags_to_extract):
            navigable_text, contact_href = get_navigable_strings(element)
            text_parts += navigable_text
            contact_hrefs += contact_href
            element.decompose()
    except Exception as e:
        print(f"Error in tags_cleaning: {e}")

    return " ".join(text_parts), contact_hrefs


# TODO : Remove it
def extract_tags(html_content, tags: List[str]) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    text_parts: List[str] = []
    contact_hrefs: List[str] = []
    for element in soup.find_all():
        if element.name in tags:
            navigable_text, contact_href = get_navigable_strings(element)
            text_parts += navigable_text
            contact_hrefs += contact_href
            element.decompose()

    return " ".join(text_parts), contact_hrefs


def remove_unnecessary_lines(content: str) -> str:
    lines = content.split("\n")
    stripped_lines = [line.strip() for line in lines]
    non_empty_lines = [line for line in stripped_lines if line]
    cleaned_content = " ".join(non_empty_lines)
    return cleaned_content


def get_navigable_strings(element: Any) -> Tuple[List[str], List[str]]:
    text_parts = []
    contact_hrefs = []

    for child in cast(Tag, element).children:
        if isinstance(child, Tag):
            child_text, child_contact_hrefs = get_navigable_strings(child)
            text_parts.extend(child_text)
            contact_hrefs.extend(child_contact_hrefs)
        elif isinstance(child, NavigableString):
            if (element.name == "a") and (href := element.get("href")):
                if href.startswith(("mailto:", "tel:")):
                    text_parts.append(f"{child.strip()} [Contact:({href})]")
                elif any(keyword in href.lower() for keyword in ["contact", "?page"]):
                    contact_hrefs.append(href)
            else:
                text_parts.append(child.strip())

    return text_parts, contact_hrefs


def preprocess_doc(doc: str, web_link: Link) -> str:
    """
    Extract text from HTML and preprocess it using BeautifulSoup.
    Also gives a list of secondary links of same domain
    """
    t_flag1 = time.time()

    tags_to_extract = (["p", "li", "div", "a", "span", "tr", "article", "h4", "h3"],)
    unwanted_tags = (
        [
            "script",
            "style",
            "noscript",
            "svg",
            "img",
            "input",
            "pre",
            "template",
        ],
    )
    _cleaned_content, secondary_links = transform_documents(
        doc, web_link, unwanted_tags, tags_to_extract
    )
    cleaned_content = remove_unnecessary_lines(_cleaned_content)

    t_flag2 = time.time()
    log.debug(f"BeautifulSoupTransformer time: {t_flag2 - t_flag1}")

    return cleaned_content, secondary_links


# def preprocess_docs(docs: List[Document]) -> List[dict]:
#     """
#     Extract text from HTML and preprocess it using BeautifulSoup
#     """
#     t_flag1 = time.time()

#     # Beautiful Soup Transformer
#     docs_transformed, site_contact_links = transform_documents(
#         docs,
#         tags_to_extract=["p", "li", "div", "a", "span", "tr", "article"],
#         unwanted_tags=[
#             "script",
#             "style",
#             "noscript",
#             "svg",
#             "img",
#             "input",
#             "pre",
#             "template",
#         ],
#     )

#     # removes long white space
#     regex_lambda = lambda x: re.sub(r"\s+", " ", x)
#     docs_transformed = document_lambda(docs_transformed, func=regex_lambda)

#     unicode_lambda = lambda x: x.encode("utf-8", errors="ignore").decode("utf-8")
#     docs_transformed = document_lambda(docs_transformed, func=unicode_lambda)

#     t_flag2 = time.time()
#     log.info(f"BeautifulSoupTransformer time: {t_flag2 - t_flag1}")

#     if LOG_FILES:
#         with open("src/log_data/docs_beautify.json", "w") as f:
#             json.dump(document2map(docs_transformed), f)

#     return docs_transformed, site_contact_links


# TODO : This is a blind split, in future we should use a contact focused split
def docs_recursive_split(
    docs: Document, chunk_size: int = 400, overlap: int = 15
) -> List[Document]:
    """
    Split the documents into chunks using RecursiveCharacterTextSplitter
    """
    t_flag1 = time.time()
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=chunk_size, chunk_overlap=overlap
    )
    splits = splitter.split_documents(docs)

    t_flag2 = time.time()
    log.info(f"RecursiveCharacterTextSplitter time: {t_flag2 - t_flag1}")

    # convert to dictoinary
    splits = document2map(splits)

    if LOG_FILES:
        with open("src/log_data/splits.json", "w") as f:
            json.dump(splits, f)

    log.info(f"Total data splits: {len(splits)}")
    return splits


def contains_contacts(text: str, email_only: bool = False) -> bool:
    """
    Check if the text contains email or phone number
    """
    # Regular expression patterns for emails and phone numbers
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    phone_pattern = r"\b(?:\+\d{1,3}\s?)?(?:\(\d{1,4}\)|\d{1,4})[\s.-]?\d{3,9}[\s.-]?\d{4}\b|\b\d{10}\b"

    contains_email = bool(re.search(email_pattern, text))
    contains_phone = bool(re.search(phone_pattern, text)) if not email_only else False

    return contains_email or contains_phone


def relevant_data(extracted_content):
    """
    Extract relevant data(checking for email and phone number) from the search results
    """
    t_flag1 = time.time()
    log.debug(f"before extraction: {len(extracted_content)}")
    data = [
        chunk
        for chunk in extracted_content
        if contains_contacts(chunk["content"], email_only=True)
    ]
    log.debug(f"after extraction: {len(data)}")
    t_flag2 = time.time()
    log.info(f"Extraction time: {t_flag2 - t_flag1}")

    if LOG_FILES:
        with open("src/log_data/context_data.json", "w") as f:
            json.dump(data, f)

    return data


def inflate_secondary_link(base_doc: dict, site_contact_links: str):
    """ """
    if isinstance(site_contact_link, list):
        combined_links = []
        for site_contact_link in site_contact_links:
            _doc = site_contact_link.copy()
            _doc["base_link"] = base_doc["link"]
            combined_links.append(_doc)
        return combined_links
    return None


def process_data_docs(html_docs: Document, chunk_size: int = 400):
    """
    Process the data by splitting it into chunks and extracting relevant data.
    """
    # _docs, site_contact_links = preprocess_docs(docs=html_docs)

    _used_docs = []
    unused_docs = []

    for doc in html_docs:
        if contains_contacts(doc.page_content, email_only=True):
            _used_docs.append(doc)
        else:
            isError = doc.metadata.get("error", None)
            if not isError:
                unused_docs.append(doc)

    log.warn(f"Length after doc regex processing: {len(_used_docs)}")

    if len(_used_docs) < 1:
        log.error("No relevant data found")
        return [], unused_docs

    data = docs_recursive_split(docs=_used_docs, chunk_size=chunk_size, overlap=15)

    data = relevant_data(extracted_content=data)

    if LOG_FILES:
        with open("src/log_data/unused_context_data.json", "w") as f:
            json.dump(document2map(unused_docs), f)

    return data, unused_docs
