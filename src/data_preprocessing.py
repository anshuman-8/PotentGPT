import json
import re
import time
import logging as log
from bs4 import BeautifulSoup, NavigableString, Tag
from typing import Dict, Any, Iterator, List, Sequence, cast
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from src.utils import create_documents, document_regex_sub, document2map


LOG_FILES = False

def transform_documents(
        documents: Sequence[Document],
        unwanted_tags: List[str] = ["script", "style"],
        tags_to_extract: List[str] = ["p", "li", "div", "a"],
        remove_lines: bool = True,
    ) -> Sequence[Document]:
        for doc in documents:
            cleaned_content = doc.page_content

            cleaned_content = remove_unwanted_tags(cleaned_content, unwanted_tags)
            cleaned_content = extract_tags(cleaned_content, tags_to_extract)

            if remove_lines:
                cleaned_content = remove_unnecessary_lines(cleaned_content)

            doc.page_content = cleaned_content

        return documents

def remove_unwanted_tags(html_content: str, unwanted_tags: List[str]) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in unwanted_tags:
        for element in soup.find_all(tag):
            element.decompose()
    return str(soup)

def extract_tags(html_content: str, tags: List[str]) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    text_parts: List[str] = []
    for element in soup.find_all():
        if element.name in tags:
            text_parts += get_navigable_strings(element)
            element.decompose()

    return " ".join(text_parts)

def remove_unnecessary_lines(content: str) -> str:
    lines = content.split("\n")
    stripped_lines = [line.strip() for line in lines]
    non_empty_lines = [line for line in stripped_lines if line]
    cleaned_content = " ".join(non_empty_lines)
    return cleaned_content

def get_navigable_strings(element: Any) -> Iterator[str]:
    for child in cast(Tag, element).children:
        if isinstance(child, Tag):
            yield from get_navigable_strings(child)
        elif isinstance(child, NavigableString):
            if (element.name == "a") and (href := element.get("href")):
                if href.startswith(("mailto:", "tel:")):
                    yield f"{child.strip()} [Contact:({href})]"
                else:
                    yield child.strip()
            else:
                yield child.strip()
            
def preprocess_text(docs: Document) -> Dict:
    """
    Extract text from HTML and preprocess it using BeautifulSoup
    """
    t_flag1 = time.time()

    # Beautiful Soup Transformer
    docs_transformed = transform_documents(
        docs,
        tags_to_extract=["p", "li", "div", "a", "span", "tr", "article"],
        unwanted_tags=["script", "style", "noscript", "svg", "img", "input", "pre", "template"],
    )
    # remove long white space
    docs_transformed = document_regex_sub(docs_transformed, r"\s+", " ")
    # remove unicode characters
    docs_transformed = document_regex_sub(docs_transformed, r"\\u[0-9A-Fa-f]{4}", "")

    t_flag2 = time.time()
    log.info(f"BeautifulSoupTransformer time: {t_flag2 - t_flag1}")

    if LOG_FILES:
        with open("src/log_data/docs_beautify.json", "w") as f:
            json.dump(document2map(docs_transformed), f)

    return docs_transformed


def docs_recursive_split(docs: Document, chunk_size: int = 400, overlap:int=50) -> List[Document]:
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


def contains_contacts(text: str, email_only:bool=False) -> bool:
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
    data = [chunk for chunk in extracted_content if contains_contacts(chunk["content"], email_only=True)]
    log.debug(f"after extraction: {len(data)}")
    t_flag2 = time.time()
    log.info(f"Extraction time: {t_flag2 - t_flag1}")

    if LOG_FILES:
        with open("src/log_data/context_data.json", "w") as f:
            json.dump(data, f)

    return data


def process_data_docs(html_docs: Document, chunk_size: int = 400):
    """
    Process the data by extracting text from HTML, splitting it into chunks and extracting relevant data
    """
    docs = preprocess_text(docs=html_docs)

    data = docs_recursive_split(docs=docs, chunk_size=chunk_size, overlap=15)

    data = relevant_data(extracted_content=data)

    return data
