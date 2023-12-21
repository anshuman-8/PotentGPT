import uuid
import logging as log
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from src.app import web_probe

app = FastAPI()


@app.get("/")
async def read_root():
    response = {"message": "Hello World", "status": "ok", "data": None}
    return response


@app.post("/q/")
async def probe(
    prompt: str | None, location: str | None, country_code: str | None = "US"
):
    ID = uuid.uuid4()
    print(ID)
    log.basicConfig(
        filename=f"logs/{ID}.log",
        filemode="w",
        format="%(name)s - %(levelname)s - %(message)s",
        level=log.INFO,
    )
    # error if prompt or location is none
    if prompt is None:
        log.error(f"No prompt provided")
        return HTTPException(status_code=400, detail="prompt needed!")
    if location is None:
        log.error(f"Location not provided")
        return HTTPException(status_code=400, detail="location needed!")
    try:
        data = await web_probe(
                id=ID, prompt=prompt, location=location, country_code=country_code
            )
    except Exception as e:
        return HTTPException(
            status_code=500, detail={"id": ID, "status":"Internal Error", "message": e}
        )
    
    return JSONResponse(content=data)
