import time
import os
import json
import logging as log
from openai import OpenAI


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


def sanitize_search_query(prompt: str,open_api_key:str, location: str = None) -> json:
    """
    Sanitize the search query using OpenAI for web search
    """
    t_flag1 = time.time()

    if open_api_key is None:
        try:
            open_api_key = os.getenv("OPENAI_API_KEY")
        except Exception as e:
            log.error(f"No Open API key found")
            raise e

    prompt = f"{prompt.strip()}"
    client = OpenAI(api_key=open_api_key)
    system_prompt = """Comprehend the goal, suggest the optimal solution, and provide small web search queries to assist in achieving it. The solution should be based on finding the best individual person or an expert, to contact for helping or completing the user goal. 
For location-based goals, prioritize location in the first query, then generalize in subsequent queries(if needed), based on finding the best expert/person/vendor for the user's goal. List the queries as strings. Give multiple search queries only if its needed and can not be done in a single search, try to keep number of queries minimum.
The output should be in JSON format, also saying where to search in a list, an enum (web, yelp, gmaps), where web is used for all cases .`yelp` and `gmaps` both are used for local businesses, including personal, small, and medium-sized enterprises, based on location. keyword is the search keyword, which is used to search for the solution, without location detail.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": f"{system_prompt}"},
                {
                    "role": "user",
                    "content": "Location: Kochi, Kerala;\nGoal: I want a good chef for my anniversary party for 50 people.",
                },
                {
                    "role": "system",
                    "content": '{"solution":"Search for all event chefs in Kochi Kerala, to email and call them", "search_query":["Event Chefs in Kochi, Kerala"], "keyword":"Event Chefs", "search":["web", "yelp"]}',
                },
                {
                    "role": "user",
                    "content": "Location: Oakland, CA;\nGoal: I want a SUV car for rent for 2 days, for a trip to Yosemite.",
                },
                {
                    "role": "system",
                    "content": '{"solution":"Search for all Car rental service in Oakland, CA, Who can give SUV and find their contacts", "search_query":["SUVs car rental in Oakland, CA"], "keyword":"Car Rental", "search":["web", "gmaps"]}',
                },
                {
                    "role": "user",
                    "content": "Location: - ;\nGoal: I need an research internship in UC Davis in molecular biology this summer.",
                },
                {
                    "role": "system",
                    "content": '{"solution": "Find all UC Davis molecular biology research professors and internship portals for emailing.", "search_query":["UC Davis professors in molecular biology contacts","UC Davis research internship","UC Davis molecular biology research labs"], "keyword": "UC Davis Professors", "search":["web"]}',
                },

                {"role": "user", "content": f"Location: {location};\nGoal: {prompt}"},
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
        if isinstance(result["search_query"], str):
            result["search_query"] = [result["search_query"]]
    except Exception as e:
        log.error(f"Error parsing json: {e}")
        result = {}
    return result