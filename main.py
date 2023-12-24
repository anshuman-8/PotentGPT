import uuid
import logging as log
import time
from typing import List
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from src.app import web_probe
from src.model import ApiResponse, ErrorResponseModel


app = FastAPI(title="Margati Probe", version="0.1.0")

@app.get("/")
async def read_root():
    response = {"status_code": 200, "message": "Hello World", "status": "ok", "data": None}
    return response



@app.post("/q/")
async def probe(
    request: Request, prompt: str | None="", location: str | None="", country_code: str | None = "US", 
) -> ApiResponse | ErrorResponseModel:
    # error if prompt or location is none
    if prompt is None or not prompt.strip():
        log.error(f"No prompt provided")
        return HTTPException(status_code=400, detail="prompt needed!")
    if location is None or not location.strip():
        log.error(f"Location not provided")
        return HTTPException(status_code=400, detail="location needed!")
        
    ID = uuid.uuid4()
    timestamp = time.strftime('%Y-%m-%d_%H:%M:%S', time.localtime())
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
        data = await web_probe(
                id=ID, prompt=prompt, location=location, country_code=country_code
            )
    except Exception as e:
        return HTTPException(
            status_code=500, detail={"id": ID, "status":"Internal Error", "message": e}
        )
    
    log.info(f"API Response: {data}")
    return JSONResponse(content=data)

