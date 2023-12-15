import time
import json
import asyncio
import logging as log
from openai import AsyncOpenAI
from typing import Iterator, List

LOG_FILES = True


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


def result_to_json(results: List[dict]) -> dict:
    """
    Convert the list of contacts to json
    """
    json_result = {"results": []}
    for result in results:
        json_result["results"].extend(result["results"])
    return json.dumps(json_result)


async def extract_thread_contacts(id: int, data, prompt: str, open_ai_key: str) -> dict:
    """
    Extract the contacts from the search results using LLM
    """

    t_flag1 = time.time()
    client = AsyncOpenAI(api_key=open_ai_key)
    log.info(f"Contact Retrival Thread {id} started")

    response = await client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": """Extract all contact details from JSON input, aiming to assist user's question in finding right service providers or vendors. Understand and comprehend whole Context data, which contains content, and provide a structured output with their respective contact details and descriptions. 
The response should strictly adhere to the JSON list format: ["results":{"service_provider": "Name and description of the service provider", "source": "Source Link of the information", "contacts": {"email": "Email of the vendor","phone": "Phone number of the vendor","address": "Address of the vendor"}},{...}].
If any fields are absent in the Context, leave them as empty as "". It is crucial not to omit any contact information. Do not give empty contacts or incorrect information.""",
            },
            {
                "role": "user",
                "content": f"Context: {data}\n\n-----\n\nQuestion: {prompt}\n\nAnswer:All relevant and accurate contact details for above Question in JSON:",
            },
        ],
    )
    t_flag2 = time.time()
    log.info(f"OpenAI time: { t_flag2 - t_flag1}")

    cost = gpt_cost_calculator(
        response.usage.prompt_tokens, response.usage.completion_tokens
    )
    log.debug(
        f"Input Tokens used: {response.usage.prompt_tokens}, Output Tokens used: {response.usage.completion_tokens}"
    )
    log.info(f"Cost for contact retrival: ${cost}\n")

    try:
        json_response = json.loads(response.choices[0].message.content)
    except Exception as e:
        log.error(f"Error parsing json: {e}")
        json_response = {}

    if LOG_FILES:
        with open("src/log_data/output.json", "w") as f:
            json.dump(json_response, f)

    # convert data to json
    response_json = json.loads(response.choices[0].message.content)

    log.info(f"Contact Retrival Thread {id} finished : {response_json}")

    return response_json


async def retrival_multithreading(
    data, prompt: str, open_ai_key: str, chunk_size: int = 5, max_thread: int = 5, timeout: int = 9
) -> dict:
    """
    Creates multiple LLM calls
    """
    llm_threads = []

    # Divide the data into chunks of size chunk_size
    data_chunks = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]
    data_chunks = data_chunks[:max_thread]

    # Create asyncio tasks for each data chunk with enumeration
    for thread_id, chunk in enumerate(data_chunks):
        task = extract_thread_contacts(thread_id, chunk, prompt, open_ai_key)
        llm_threads.append(task)

    # Set a timeout for each thread
    timeout_tasks = [asyncio.wait_for(task, timeout) for task in llm_threads]

    try:
        results = await asyncio.gather(*timeout_tasks)
    except asyncio.TimeoutError as e:
        print(f"LLM Timeout error: {e}")
        results = []

    results = result_to_json(results)

    return results


def llm_contacts_retrival(data, prompt: str, open_ai_key: str) -> dict:
    """
    Extract the contacts from the search results using LLM
    """
    results = asyncio.run(retrival_multithreading(data, prompt, open_ai_key, 5))
    return results
