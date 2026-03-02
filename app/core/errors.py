from dataclasses import dataclass
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


@dataclass
class AppError(Exception):
    error_code: str
    message: str
    status_code: int = 400
    details: dict | None = None


class ErrorCodes:
    AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN"
    AUTH_FORBIDDEN = "AUTH_FORBIDDEN"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    DB_CONFLICT = "DB_CONFLICT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id", str(uuid4()))


def _json_error(
    request: Request,
    error_code: str,
    message: str,
    status_code: int,
    details: dict | list | None = None,
) -> JSONResponse:
    payload = {
        "error_code": error_code,
        "message": message,
        "details": jsonable_encoder(details) if details is not None else None,
        "request_id": _request_id(request),
    }
    return JSONResponse(status_code=status_code, content=payload)


def register_exception_handlers(app) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        return _json_error(request, exc.error_code, exc.message, exc.status_code, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        return _json_error(
            request,
            ErrorCodes.VALIDATION_ERROR,
            "Validation failed",
            422,
            exc.errors(),
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException):
        code = ErrorCodes.INTERNAL_ERROR
        if exc.status_code == 401:
            code = ErrorCodes.AUTH_INVALID_TOKEN
        elif exc.status_code == 403:
            code = ErrorCodes.AUTH_FORBIDDEN
        elif exc.status_code == 404:
            code = ErrorCodes.NOT_FOUND
        return _json_error(request, code, str(exc.detail), exc.status_code)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        return _json_error(
            request,
            ErrorCodes.INTERNAL_ERROR,
            "Internal server error",
            500,
        )
