import time
import json
import asyncio
import logging as log
from openai import AsyncOpenAI, OpenAI
from typing import Iterator, List

LOG_FILES = True

SYS_PROMPT = """Extract all contact details from JSON input, aiming to assist user's question in finding right service providers or vendors. Response should be relevant to the question and accurate to the context.
The response should strictly adhere to the JSON list format: ["results":{"service_provider": "Name and description of the service provider", "source": "Source Link of the information","provider":["Source from "Google", "Bing" or both"], "contacts": {"email": "Email of the vendor","phone": ["Phone number of the vendor"],"address": "Address of the vendor"}},{...}].
Ensure all fields in the context are filled; use empty list if absent. Avoid providing incorrect or empty contact details. Present phone numbers and emails in a direct, usable format(no helper words).
\nExample response (Only as an exmple format, data not to be used) : \n["results":{"service_provider": "One Toyota | New Toyota & Used Car Dealer in Oakland", "source": "https://www.onetoyota.com/","provider":["Google", "Bing"], "contacts": {"email": [],"phone": ["510-281-8909", "510-281-8910"],"address": "8181 Oakport St. Oakland, CA 94621"}}]\n"""

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
        if result == {}:
            continue

        json_result["results"].extend(result["results"])
    return json.dumps(json_result)


def print_and_write_response(response_json, output_file="output.txt"):
    """
    Print and write the response to a file
    """
    print("\n")

    if isinstance(response_json, dict) and "results" in response_json:
        results = response_json["results"]
    elif isinstance(response_json, list):
        results = response_json
    else:
        print("Invalid input. Please provide a valid JSON object or a list of them.")
        return

    with open(output_file, "a") as file:
        for service in results:
            file.write(f"Service Provider: {service.get('service_provider', '')}\n")
            file.write(f"Source: {service.get('source', '')}\n")

            contacts = service.get("contacts", {})
            file.write(f"Contacts:\n")
            file.write(f"\tEmail: {contacts.get('email', '')}\n")
            file.write(f"\tPhone: {contacts.get('phone', '')}\n")
            file.write(f"\tAddress: {contacts.get('address', '')}\n")

            file.write("\n" + "-" * 40 + "\n\n")

            # Print to console
            print(f"Service Provider: {service.get('service_provider', '')}")
            print(f"Source: {service.get('source', '')}")
            print(f"Contacts:")
            print(f"\tEmail: {contacts.get('email', '')}")
            print(f"\tPhone: {contacts.get('phone', '')}")
            print(f"\tAddress: {contacts.get('address', '')}")
            print("\n" + "-" * 40 + "\n")


async def extract_thread_contacts(id: int, data, prompt: str, openai_client) -> dict:
    """
    Extract the contacts from the search results using LLM
    """

    t_flag1 = time.time()
    log.warning(f"this should run!")
    log.info(f"Contact Retrival Thread {id} started")

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": SYS_PROMPT,
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
        log.info(f"Cost for contact retrival {id}: ${cost}\n")

        response = json.loads(response.choices[0].message.content)
        # Print the response
        # print_and_write_response(response, output_file="src/output.txt")

        log.info(f"Contact Retrival Thread {id} finished : {response}")

    except Exception as e:
        log.error(f"Error in {id} LLM API call: {e}")
        response = {}

    yield response


async def retrieval_multithreading(
    data,
    prompt: str,
    open_ai_key: str,
    chunk_size: int = 5,
    max_thread: int = 5,
    timeout: int = 10,
) -> dict:
    """
    Creates multiple LLM calls
    """
    # Divide the data into chunks of size chunk_size
    data_chunks = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]
    data_chunks = data_chunks[:max_thread]

    try:
        llm_threads = []
        client = AsyncOpenAI(api_key=open_ai_key, max_retries=0)

        # Create asyncio tasks for each data chunk with enumeration
        for thread_id, chunk in enumerate(data_chunks):
            task = asyncio.create_task(extract_thread_contacts(thread_id + 1, chunk, prompt, client))
            llm_threads.append(task)

        for task in asyncio.as_completed(llm_threads):
            result = await task
            yield result

    except Exception as e:
        log.error(f"Error in multithreading: {e}")
        yield b'{}'


async def llm_contacts_retrieval(id:str, data, prompt: str, open_ai_key: str) -> dict:
    """
    Extract the contacts from the search results using LLM
    """
    async for results in retrieval_multithreading(data, prompt, open_ai_key, 5):
        yield results


def extract_contacts(data, prompt: str, openai_key) -> str:
    """
    Extract the contacts from the search results using LLM
    """
    # TODO: Take on max first 15 of the components of the data json

    t_flag1 = time.time()
    client = OpenAI(api_key=openai_key)

    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        # timeout=8,
        # temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": SYS_PROMPT,
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
    log.info(f"Cost for contact retrival: ${cost}")

    try:
        json_response = json.loads(response.choices[0].message.content)
    except Exception as e:
        log.error(f"Error parsing json: {e}")
        json_response = {}

    return json_response
