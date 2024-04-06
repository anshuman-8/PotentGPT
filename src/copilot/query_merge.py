import os
import time 
import logging as log
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()

MY_ENV_VAR = os.getenv('OPENAI_API_KEY')


System_Prompt_question_gen = "Given the user's goal and the questions asked to the user with its answers, merge the questions into the goal to make it less vague. If the goal is already well described, respond with the goal as it is.\nAlso assign tags(max 2) to the goals form the list -\"Education\",\"Internship\",\"Equipment\",\"Research\",\"Sales\",\"Entrepreneurship\",\"Logistics\",\"Relocation\",\"Tutoring\",\"Travel\",\"Rental\",\"Food & Beverages\",\"Real Estate\",\"Health & Fitness\",\"Technology\",\"Finance\",\"Medical Services\",\"Skilled Services\",\"Volunteer Work\",\"Personal Growth\",\"Hobbies\",\"Retirement\",\"Style & Fashion\",\"Adventure Sports\",\"Music & Entertainment\",\"Jobs\",\"Higher Studies\",\"Hardware Fix\", \"Equipments\", \"Large Equipments\", \"Car\". Give empty list if none. \nRespond in JSON, Format - {\"merged_goal\":\"\", \"tags\": []}"

question_gen_few_shot = [ {
                    "role": "user",
                    "content": "Goal: I want a new car,  User Choices: What type of car do you want? - SUV, Which brand of car do you prefer? - Toyota, Location: Oakland, CA",
                },
                {
                    "role": "system",
                    "content": "{\"merged_goal\":\"I want a new Toyota SUV car in Oakland, CA\", \"tags\":[\"Car\"]}",
                }]

def merge_goal(choices:dict, goal:str):
    """
    Reframe and generates goal query based on the user's choses and preferences
    """
    start_time = time.time()
    client = OpenAI(api_key=MY_ENV_VAR)
    if not choices:
        raise Exception("No choices provided")
    
    if not goal:
        raise Exception("No goal provided")
    
    choices_str = prepare_choice(choices)

    try :
        response = client.chat.completions.create(
        model= "gpt-3.5-turbo",
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": System_Prompt_question_gen},
            *question_gen_few_shot,
            {"role": "user", "content": f"Goal:{goal}, User Choices:{choices_str}"},
        ]
        )
    except Exception as e:
        log.error("Error OpenAI API call : {e}")
        raise Exception("Error OpenAI API call")

    end_time = time.time()
   
    log.info(f'Time Taken: {end_time - start_time} Sec\n')

    question_list = json_analyzer(response.choices[0].message.content)

    return question_list

def prepare_choice(choices:dict):
    """
    Prepares the choices for the OpenAI API
    """
    choice_str = ""

    for choice in choices["choices"]:
        if choice["answer"] == "" or choice["answer"] == None:
            continue
        choice_str += f"{choice["question"]}: {choice["answer"]}, "
    return choice_str


def json_analyzer(data:str):
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