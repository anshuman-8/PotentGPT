import uuid
import time
import logging as log
from typing import List
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from src.app import (
    web_probe,
    response_formatter,
    stream_contacts_retrieval,
)
from src.model import ApiResponse, ErrorResponseModel
import tracemalloc

tracemalloc.start()

app = FastAPI(title="Margati Probe", version="0.1.0")


@app.get("/")
async def read_root():
    response = {
        "status_code": 200,
        "message": "Hello World",
        "status": "ok",
        "data": None,
    }
    return response


async def stream_response(id, data, prompt, solution, location, start_time):
    async for chunk in stream_contacts_retrieval(id, data, prompt, solution):
        end_time = time.time()
        response = await response_formatter(
            id, (end_time - start_time), prompt, location, chunk
        )
        log.info(f"\nStreaming Response: {response}")
        yield response
    
    final_response = await response_formatter(id, (end_time - start_time), prompt, location, [], status="completed", has_more=False)
    log.info(f"\nStreaming Final Response: {final_response}")
    yield final_response


@app.get("/q/")
async def probe(
    request: Request,
    prompt: str | None = "",
    location: str | None = "",
    country_code: str | None = "US",
) -> ApiResponse | ErrorResponseModel:
    
    if prompt is None or not prompt.strip():
        log.error(f"No prompt provided")
        raise HTTPException(status_code=400, detail="prompt needed!")
    if location is None or not location.strip():
        log.error(f"Location not provided")
        raise HTTPException(status_code=400, detail="location needed!")

    ID = uuid.uuid4()
    start_time = time.time()
    timestamp = time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime())
    print(ID)
    log.basicConfig(
        filename=f"logs/{ID}.log",
        filemode="w",
        format="%(name)s - %(levelname)s - %(message)s",
        level=log.INFO,
    )
    log.info(f"Request: {prompt}, {location}, {country_code}")
    log.info(f"Request from: {request.client.host}")
    log.info(f"Total Time: {timestamp}")
    try:
        data, solution = await web_probe(
            id=ID, prompt=prompt, location=location, country_code=country_code
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail={"id": str(ID), "status": "Internal Error", "message": str(e)}
        )

    return StreamingResponse(
        content=stream_response(ID, data, prompt, solution, location, start_time)
    )
