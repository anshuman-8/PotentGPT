import uuid
import logging as log
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from src.app import web_probe, contacts_retrieval

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
    
    data = await web_probe(
            id=ID, prompt=prompt, location=location, country_code=country_code
        )


    return JSONResponse(content=data, status_code=200)

    # return StreamingResponse(contacts_retrieval(ID, prompt=prompt, context_data=data), media_type="application/json")
