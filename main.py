import uuid
import time
import json
import logging as log
from typing import List
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, Response
from src.app import (
    search_query_extrapolate,
    extract_web_context,
    response_formatter,
    stream_contacts_retrieval,
    static_contacts_retrieval,
)
from src.model import ApiResponse, ErrorResponseModel, RequestContext, Feedback
import tracemalloc

tracemalloc.start()

app = FastAPI(title="Margati Probe", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_root():
    response = {
        "status_code": 200,
        "message": "Hello World",
        "status": "ok",
        "data": None,
    }
    return response


async def stream_response(request_context: RequestContext, data: List[dict]):
    async for chunk in stream_contacts_retrieval(request_context, data):
        end_time = time.time()
        request_context.add_contacts(chunk)
        response = await response_formatter(
            request_context.id,
            (end_time - request_context.start_time),
            request_context.prompt,
            request_context.location,
            chunk,
            request_context.solution,
            request_context.search_space,
            request_context.search_query,
        )
        log.info(f"\nStreaming Response: {response}")
        yield response

    final_response = await response_formatter(
        request_context.id,
        (end_time - request_context.start_time),
        request_context.prompt,
        request_context.location,
        request_context.contacts,
        request_context.solution,
        request_context.search_space,
        request_context.search_query,
        status="completed",
        has_more=False,
    )
    log.info(f"\nStreaming Final Response: {final_response}")

    date = time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime())
    with open(f"response-logs/{date}.json", "w") as f:
        f.write(str(final_response))

    yield final_response


async def static_response(request_context: RequestContext, data: List[dict]):
    results = await static_contacts_retrieval(request_context, data)

    end_time = time.time()
    response = await response_formatter(
        request_context.id,
        (end_time - request_context.start_time),
        request_context.prompt,
        request_context.location,
        results,
        request_context.solution,
        request_context.search_space,
        request_context.search_query,
        status="completed",
        has_more=False,
    )
    log.info(f"\nStatic Response: {response}")
    date = time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime())
    with open(f"response-logs/{date}.json", "w") as f:
        f.write(str(response))
    return response


@app.get("/q/")
async def probe(
    request: Request,
    prompt: str | None = "",
    location: str | None = "",
    country_code: str | None = "US",
) -> ApiResponse | ErrorResponseModel:
    ID = uuid.uuid4()
    timestamp = time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime())
    print(ID)

    log.basicConfig(
        filename=f"logs/{ID}.log",
        filemode="w",
        format="%(name)s - %(levelname)s - %(message)s",
        level=log.INFO,
    )

    if prompt is None or not prompt.strip():
        log.error(f"No prompt provided")
        raise HTTPException(status_code=400, detail="prompt needed!")
    if location is None or not location.strip():
        log.error(f"Location not provided")
        raise HTTPException(status_code=400, detail="location needed!")

    request_context = RequestContext(str(ID), prompt, location, country_code)

    log.info(f"Request: {prompt}, {location}, {country_code}")
    log.info(f"Request from: {request.client.host}")
    log.info(f"Total Time: {timestamp}")

    try:
        query, solution, search_space = search_query_extrapolate(
            request_context=request_context,
        )
        request_context.update_search_param(query, solution, search_space)

        web_context = await extract_web_context(request_context=request_context)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"id": str(ID), "status": "Internal Error", "message": str(e)},
        )

    return StreamingResponse(content=stream_response(request_context, web_context))


@app.get("/static/")
async def staticProbe(
    request: Request,
    prompt: str | None = "",
    location: str | None = "",
    country_code: str | None = "US",
) -> ApiResponse | ErrorResponseModel:
    ID = uuid.uuid4()
    timestamp = time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime())
    print(ID)

    log.basicConfig(
        filename=f"logs/{ID}.log",
        filemode="w",
        format="%(name)s - %(levelname)s - %(message)s",
        level=log.INFO,
    )

    if prompt is None or not prompt.strip():
        log.error(f"No prompt provided")
        raise HTTPException(status_code=400, detail="prompt needed!")
    if location is None or not location.strip():
        log.error(f"Location not provided")
        raise HTTPException(status_code=400, detail="location needed!")

    request_context = RequestContext(str(ID), prompt, location, country_code)

    log.info(f"Request: {prompt}, {location}, {country_code}")
    log.info(f"Request from: {request.client.host}")
    log.info(f"Total Time: {timestamp}")

    try:
        query, solution, search_space = search_query_extrapolate(
            request_context=request_context,
        )
        request_context.update_search_param(query, solution, search_space)

        web_context = await extract_web_context(request_context=request_context)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"id": str(ID), "status": "Internal Error", "message": str(e)},
        )

    response = await static_response(request_context, web_context)

    return Response(content=response)


@app.post("/feedback/")
async def feedback(request: Request, feedback: Feedback) -> JSONResponse:
    date = time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime())

    feedback_data = {
        "request_id": feedback.id,
        "feedback": feedback.message,
        "rating": feedback.rating,
        "prompt": feedback.prompt,
        "user_ip": request.client.host,
        "user_agent": request.headers["user-agent"],
        "timestamp": date,
        "data": feedback.data,
    }

    with open(f"feedbacks/{date}_{feedback.id}.json", "w") as f:
        json.dump(feedback_data, f)

    return JSONResponse(
        content={
            "status": "ok",
            "message": "Feedback received",
        },
        status_code=200,
    )
