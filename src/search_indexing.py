import json
from typing import List, Dict, Tuple
from urllib.parse import urlparse

def extract_domain(url):
    """
    This function takes a url and returns the domain name.
    """
    parsed_url = urlparse(url)

    domain_name = parsed_url.netloc
    return domain_name

def search_indexing(bing_search:dict | None, google_search:dict | None) -> dict:
    """
    This function takes the bing and google search results and returns a combined dictionary of all search links.
    """
    if not bing_search:
        return google_search
    elif not google_search:
        return bing_search
    
    search_index = {}

    for results, source in zip([google_search, bing_search], ['google', 'bing']):
        for result in results:
            search_link = extract_domain(result['link'])

            if search_link in search_index:
                # Update the existing result with the new index
                search_index[search_link]['index'].append(result['index'])
                if source not in search_index[search_link]['source']:
                    search_index[search_link]['source'].append(source)
            else:
                # Add a new entry to the merged results
                search_index[search_link] = {
                    'index': [result['index']],
                    'title': result['title'],
                    'link': result['link'],
                    'displayLink': search_link,
                    'source': [source]
                }

    final_result = list(search_index.values())

    # write to file
    with open('src/log_data/search_index.json', 'w') as f:
        json.dump(final_result, f, indent=4)

    return final_result
    

