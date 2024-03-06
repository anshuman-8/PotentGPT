import os
import time 
import logging as log
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()

MY_ENV_VAR = os.getenv('OPENAI_API_KEY')


System_Prompt_question_gen = "Below is the user's goal or task, based on clear understanding give the following in JSON:\n- List of top(max 5) very important questions for the user with options to improve the goal statement and make the goal less vague. Questions to be asked to remove vagueness and improvement for more clarity for others. Its type can be \"choice\",  \"input\" or \"date\", if input then give options as empty list(but prefer choice over input). Do not ask questions only if it's very well described(respond with empty list for questions). \n- State weather if it is a product, service or invalid goal (in goal_type), invalid when its invalid or inappropriate. Format - {\"questions\":[{\"question\":\"\",\"type\":\"\",\"options\":[\"\",\"\"],},{}],\"goal_type\":\"\"}"

question_gen_few_shot = [ {
                    "role": "user",
                    "content": "Location: Oakland, CA;\nGoal: I want a new car",
                },
                {
                    "role": "system",
                    "content": "{\"questions\":[{\"question\":\"What type of car do you want?\",\"type\":\"choice\",\"options\":[\"SUV\", \"Sedan\", \"Truck\", \"Coupe\"]},{\"question\":\"What is the budget for the car?\",\"type\":\"choice\",\"options\":[\"$1000\", \"$2000\", \"$3000\", \"$4000\"]},{\"question\":\"Which brand of car do you prefer?\",\"type\":\"choice\",\"options\":[\"Toyota\", \"Honda\", \"Ford\", \"Chevrolet\"]}],\"goal_type\":\"product\"}",
                },
                {
                    "role": "user",
                    "content": "Goal:I want to do an internship in UC Davis in the fiels of Microbiology.",
                },
                { "role": "system",
                 "content": "{\"questions\":[{\"question\":\"What is the duration of the internship?\",\"type\":\"choice\",\"options\":[\"1 month\", \"2 months\", \"3 months\", \"4 months\"]},{\"question\":\"What type of internship do you want?\",\"type\":\"choice\",\"options\":[\"Paid\",\"Un-Paid\"]},{\"question\":\"What is the field of study?\",\"type\":\"input\",\"options\":[]}],\"goal_type\":\"service\"}"
                }
                ]

def generate_question(query:str, location:str|None):
    """
    Generates questions based on the user's goal or task
    """
    start_time = time.time()
    client = OpenAI(api_key=MY_ENV_VAR)
    location_string = ""
    if location:
        location_string = f"Location:{location},\n"

    try :
        response = client.chat.completions.create(
        model= "gpt-3.5-turbo",
        response_format={ "type": "json_object" },
        
        messages=[
            {"role": "system", "content": System_Prompt_question_gen},
            *question_gen_few_shot,
            {"role": "user", "content": f"{location_string}Goal:{query}"},
        ]
        )
    except Exception as e:
        log.error("Error OpenAI API call : {e}")
        raise Exception("Error OpenAI API call")

    end_time = time.time()
    # print(response)

    # print(f'Total Tokens:{response.usage.total_tokens}, Prompt Token {response.usage.prompt_tokens}, Completion Token {response.usage.completion_tokens}')
    log.info(f'Time Taken: {end_time - start_time} Sec\n')

    # response = json.loads(response.choices[0].message.content)
    # print(json.dumps(response, indent=4))

    question_list = json_analyzer(response.choices[0].message.content)

    return question_list


def json_analyzer(data:str):
    """
    Converts the string to json, and returns if in correct format

    format
    {
    "questions":{
        "question": {type:string},
        "type": {type:string},
        "options":{type:List[string]}
    },
    "goal_type": {type:string}   
    }
    """
    try:
        json_data = json.loads(data)

    except Exception as e:
        log.error("Error in parsing OpenAI response")

    return json_data