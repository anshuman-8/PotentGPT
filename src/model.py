from pydantic import BaseModel
from typing import List

class ContactDetails(BaseModel):
    email: str = ""
    phone: List[str] = []
    address: str = ""


class ServiceProvider(BaseModel):
    service_provider: str
    source: str
    provider: List[str]
    contacts: ContactDetails


class ApiResponse(BaseModel):
    id: str
    status: str
    prompt: str
    location: str
    country: str
    run_time: int
    results: List[ServiceProvider]


class ErrorResponseModel(BaseModel):
    id: str
    prompt: str
    status: str = "error"
    message: str
