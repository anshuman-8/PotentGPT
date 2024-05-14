import os
import time
import logging as log
from openai import OpenAI
from typing import List
import json
from src.config import Config

config = Config()


System_Prompt_question_gen = 'Based on the leverage of the user or of the service/product provider given in the targets, give 3-4 most appropriate questions user can/should ask the targets them about their offering as first person. If its a service the questions should be towards the individual person giving service or performing the craft. The response should be in JSON format. Follow format {"questions":["",""]}'


def generate_questions(vendor_targets: List[str], goal: str):
    """
    Reframe and generates goal query based on the user's choses and preferences
    """
    start_time = time.time()
    client = OpenAI(api_key=config.get_openai_api_key())
    if not vendor_targets:
        raise Exception("No choices provided")

    if not goal:
        raise Exception("No goal provided")

    try:
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            response_format={"type": "json_object"},
            temperature=0.3,
            messages=[
                {"role": "system", "content": System_Prompt_question_gen},
                {
                    "role": "user",
                    "content": f"Goal:{goal}, Provider Targets:{vendor_targets}",
                },
            ],
        )
    except Exception as e:
        log.error("Error OpenAI API call : {e}")
        raise Exception("Error OpenAI API call")

    end_time = time.time()

    log.info(f"Time Taken: {end_time - start_time} Sec\n")

    question_list = json_analyzer(response.choices[0].message.content)

    return question_list


def prepare_choice(choices: dict):
    """
    Prepares the choices for the OpenAI API
    """
    choice_str = ""

    for choice in choices["choices"]:
        if choice["answer"] == "" or choice["answer"] == None:
            continue
        choice_str += f"{choice["question"]}: {choice["answer"]}, "
    return choice_str


def json_analyzer(data: str):
    """
    Converts the string to json, and returns if in correct format

    format
    {
    "merged_goal": {type:string}
    }
    """
    try:
        json_data = json.loads(data)

    except Exception as e:
        log.error("Error in parsing OpenAI response")

    return json_data
