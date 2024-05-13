import uuid
import uvicorn
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
    static_contacts_retrieval,
)
from src.model import (
    ApiResponse,
    ErrorResponseModel,
    RequestContext,
    Feedback,
    CpAPIResponse,
    CpMergeRequest,
    YelpReverseSearchRequest,
    VendorQuestionRequest,
)
from src.copilot.question_generation import generate_question
from src.copilot.query_merge import merge_goal
from src.lmBasic.titleGenerator import generate_title
from src.search import Search
from src.vendor_question import generate_questions
import tracemalloc

tracemalloc.start()

app = FastAPI(title="Margati Probe", version="0.2.0")

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


@app.get("/static/")
async def staticProbe(
    request: Request,
    prompt: str | None = "",
    location: str | None = "",
    country_code: str | None = "US",
) -> ApiResponse | ErrorResponseModel:
    ID = uuid.uuid4()
    timestamp = time.strftime("%m-%d_%H:%M:%S", time.localtime())
    file_name = f"logs/s-{timestamp}-{ID}.log"
    log.basicConfig(
        filename=file_name,
        filemode="w",
        format="%(levelname)s - %(message)s",
        level=log.INFO,
    )
    print(f"\n{file_name}\n")

    if prompt is None or not prompt.strip():
        log.error(f"No prompt provided")
        raise HTTPException(status_code=400, detail="prompt needed!")
    if location is None or not location.strip():
        log.error(f"Location not provided")
        raise HTTPException(status_code=400, detail="location needed!")

    request_context = RequestContext(str(ID), prompt, location, country_code)

    log.info(f"Request: {prompt}, {location}, {country_code}")
    log.info(f"Request from: {request.client.host}")
    log.info(f"Time: {timestamp}")

    try:
        target, query, goal_type = search_query_extrapolate(
            request_context=request_context,
        )
        request_context.update_search_param(target, query, goal_type)
        log.info(f"Updated request context !")
        log.debug(request_context.__dict__)
        web_context = await extract_web_context(
            request_context=request_context, deep_scrape=True
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"id": str(ID), "status": "Internal Error", "message": str(e)},
        )

    response = await static_contacts_retrieval(request_context, web_context)

    return Response(content=response)


@app.post("/static/reverse-yelp/")
async def reverseSearchYelp(
    request: YelpReverseSearchRequest,
) -> JSONResponse:
    vendor_name = request.vendor.name
    location = request.location

    if location is None or not location.strip():
        raise HTTPException(status_code=400, detail="location needed!")

    search = Search.yelp_reverse_search(vendor_name, location)

    if search is None or search == {}:
        raise HTTPException(status_code=404, detail="No results found")

    return JSONResponse(content=search)


@app.get("/title/")
async def title(
    request: Request,
    goal: str | None,
) -> JSONResponse:
    ID = uuid.uuid4()
    timestamp = time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime())

    log.basicConfig(
        filename=f"logs/title-{ID}.log",
        filemode="w",
        format="%(name)s - %(levelname)s - %(message)s",
        level=log.INFO,
    )

    if goal is None or not goal.strip():
        log.error(f"No goal provided")
        raise HTTPException(status_code=400, detail="goal needed!")

    try:
        response = generate_title(goal)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"status": "Internal Error", "message": str(e)},
        )

    return JSONResponse(content=response)


@app.get("/copilot/")
async def copilot(
    request: Request,
    prompt: str | None,
    location: str | None,
) -> CpAPIResponse | ErrorResponseModel:
    ID = uuid.uuid4()
    timestamp = time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime())

    log.basicConfig(
        filename=f"logs/cp-{ID}.log",
        filemode="w",
        format="%(name)s - %(levelname)s - %(message)s",
        level=log.INFO,
    )

    if prompt is None or not prompt.strip():
        log.error(f"No prompt provided")
        raise HTTPException(status_code=400, detail="prompt needed!")

    try:
        response = generate_question(prompt, location)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"status": "Internal Error", "message": str(e)},
        )

    return JSONResponse(content=response)


@app.post("/copilot/merge/")
def cpMerge(request: CpMergeRequest) -> CpAPIResponse | ErrorResponseModel:

    try:
        response = merge_goal(request.choices, request.goal)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"status": "Internal Error", "message": str(e)},
        )
    return JSONResponse(response)


@app.post("/vendor-question")
async def vendor_question(request: VendorQuestionRequest) -> JSONResponse:

    vendor_targets = request.vendor_targets
    goal = request.goal

    if not vendor_targets:
        raise Exception("No choices provided")

    if not goal:
        raise Exception("No goal provided")

    try:
        response = generate_questions(vendor_targets, goal)
    except Exception as e:
        raise Exception("Error OpenAI API call")

    return JSONResponse(content=response)


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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
