from langchain.docstore.document import Document
import logging as log
from typing import Iterator, List, Optional
import copy
import re


def create_documents( texts: List[str], metadatas: Optional[List[dict]] = None
) -> List[Document]:
    """Create documents from a list of texts."""
    _metadatas = metadatas or [{}] * len(texts)
    documents = []
    for i, text in enumerate(texts):
        metadata = copy.deepcopy(_metadatas[i])
        new_doc = Document(page_content=text, metadata=metadata)
        documents.append(new_doc)
    return documents

def document_regex_sub(documents: List[Document], pattern: str, repl: str) -> List[Document]:
    """Filter documents based on a regex pattern."""
    texts, metadatas = [], []
    for doc in documents:
        texts.append(doc.page_content)
        metadatas.append(doc.metadata)
    texts = [re.sub(pattern, repl, text) for text in texts]
    return create_documents(texts, metadatas=metadatas)

def document2map(documents: List[Document]) -> List[dict]:
    """Convert a list of documents to a map."""
    log.info("Converting documents to map...")
    return [ {"metadata" : doc.metadata['source'] ,"content": doc.page_content} for doc in documents]