from langchain.docstore.document import Document
import logging as log
import json
from typing import Iterator, List, Optional
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
        {"metadata": doc.metadata, "content": doc.page_content}
        for doc in documents
    ]

def process_api_json(response):
    """
    Process the API response
    """
    log.info(f"Processing API response : {response}")
    # Initialize an empty list to store processed results
    processed_results = []
    
    try:
        # Iterate over each result in the input data
        for result in response.get('results', []):
            if isinstance(result, str):
                try:
                    result = json.loads(result)  # Assuming result is a JSON string
                except json.JSONDecodeError:
                    result = {}
                    
            # Extract contacts and initialize empty lists for email and phone
            contacts = result.get('contacts', {})
            emails = []
            phones = []
            
            # Process emails using regex to extract valid formats
            if contacts.get('email'):
                if isinstance(contacts['email'], list):
                    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', ', '.join(contacts['email']))
                else:
                    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', contacts['email'])
            
            # Process phone numbers using regex to extract valid formats
            if contacts.get('phone'):
                if isinstance(contacts['phone'], list):
                    phones = re.findall(r'\b(?:\+\d{1,3}\s?)?(?:\(\d{1,4}\)|\d{1,4})[\s.-]?\d{3,9}[\s.-]?\d{4}\b|\b\d{10}\b', ', '.join(contacts['phone']))
                else:
                    phones = re.findall(r'\b(?:\+\d{1,3}\s?)?(?:\(\d{1,4}\)|\d{1,4})[\s.-]?\d{3,9}[\s.-]?\d{4}\b|\b\d{10}\b', contacts['phone'])
            
            # Create a new processed result dictionary
            processed_result = {
                'name': result.get('name', ''),
                'source': result.get('source', ''),
                'provider': result.get('provider', []),
                'contacts': {
                    'email': emails if emails else [],
                    'phone': phones if phones else [],
                    'address': contacts.get('address', '')
                }
            }
            
            # Append the processed result to the list
            processed_results.append(processed_result)
        
        # Create the processed JSON response
        processed_json = {
            'id': response.get('id', ''),
            'has_more': response.get('has_more', False),
            'prompt': response.get('prompt', ''),
            'location': response.get('location', ''),
            'time': response.get('time', 0),
            'count': response.get('count', 0),
            'results': processed_results
        }
    except Exception as e:
        log.error(f"Error processing API response : {e}")
        raise Exception("Error processing API response")
    
    return processed_json

