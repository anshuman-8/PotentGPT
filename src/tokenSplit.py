from typing import List, Optional
import tiktoken

class Tokenizer:
    """Tokenizer class."""
    def __init__(self, encoding_name: str = None, model_name: Optional[str] = 'gpt-3.5-turbo'):

        if encoding_name is not None:
            enc = tiktoken.get_encoding(encoding_name)
        else:
            enc = tiktoken.encoding_for_model(model_name)
        
        self.tokenizer = enc
    
    def encode(self, text: str) -> List[int]:
        return self.tokenizer.encode(text)

    def decode(self, token_ids: List[int]) -> str:
        return self.tokenizer.decode(token_ids)

def split_text_on_tokens_custom(
    text: str,
    tokenizer: Tokenizer,
    token_size: int,
    overlap: Optional[int] = 0
) -> List[str]:
    """Split incoming text using a custom tokenizer based on token size and overlap."""
    splits: List[str] = []
    
    def recursive_split(start_idx):
        end_idx = min(start_idx + token_size, len(text))
        chunk_ids = tokenizer.encode(text[start_idx:end_idx])
        splits.append(tokenizer.decode(chunk_ids))
        
        if end_idx < len(text):
            next_start_idx = end_idx - overlap
            recursive_split(next_start_idx)
    
    recursive_split(0)
    
    return splits

