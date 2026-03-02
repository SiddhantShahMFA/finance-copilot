from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: dict | list | None = None
    request_id: str


class HealthResponse(BaseModel):
    status: str
    version: str
    db_connected: bool
