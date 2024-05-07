import os
import time
import logging as log
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()

MY_ENV_VAR = os.getenv("OPENAI_API_KEY")

System_Prompt_title_gen = 'Give an appropriate title (just as a summary) for the given goal(not more than 8-9 words). Make it like in third person. Respond with the title in JSON format. Also assign tags to the goal (like- "Higher Education", "Car Rental" etc). Give tags (max 4 & min 2) in a list. Format- {"title":" ", "tags":[" "," "]}'


def generate_title(goal: str):
    """
    Generates questions based on the user's goal or task
    """
    start_time = time.time()
    client = OpenAI(api_key=MY_ENV_VAR)

    if goal is None or goal == "":
        raise ValueError("Goal is None")

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": System_Prompt_title_gen},
                # *question_gen_few_shot,
                {"role": "user", "content": f"Goal:{goal}"},
            ],
        )
    except Exception as e:
        log.error("Error OpenAI API call : {e}")
        raise Exception("Error OpenAI API call")

    end_time = time.time()

    log.info(f"Time Taken: {end_time - start_time} Sec\n")

    title = json_analyzer(response.choices[0].message.content)

    return title


def json_analyzer(json_str: str):
    """ """
    try:
        response = {}
        json_obj = json.loads(json_str)
        tags = []
        if isinstance(json_obj["tags"], list):
            tags = [tag.strip() for tag in json_obj["tags"]]
        elif isinstance(json_obj["tags"], str):
            tags = json_obj["tags"]

        response = {"title": json_obj["title"], "tags": tags}

    except Exception as e:
        log.error(f"Error in JSON parsing: {e}")
        raise Exception("Error in JSON parsing")

    return response
