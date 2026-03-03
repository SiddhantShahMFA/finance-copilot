from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import ErrorCodes
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.observability import observability_store
from app.core.rate_limit import InMemoryRateLimiter

settings = get_settings()
_protected_prefixes = [p.strip() for p in settings.rate_limit_path_prefixes.split(",") if p.strip()]
rate_limiter = InMemoryRateLimiter(settings.rate_limit_requests, settings.rate_limit_window_seconds)

configure_logging()
app = FastAPI(title=settings.app_name, version=settings.api_version)


@app.middleware("http")
async def hardening_middleware(request: Request, call_next):
    start = perf_counter()
    path = request.url.path
    method = request.method

    if settings.rate_limit_enabled and any(path.startswith(prefix) for prefix in _protected_prefixes):
        identifier = request.headers.get("authorization")
        if not identifier:
            identifier = request.client.host if request.client else "anonymous"
        if not rate_limiter.allow(f"{path}|{identifier}"):
            response = JSONResponse(
                status_code=429,
                content={
                    "error_code": ErrorCodes.RATE_LIMIT_EXCEEDED,
                    "message": "Rate limit exceeded. Please retry later.",
                    "details": {"path": path},
                    "request_id": request.headers.get("x-request-id"),
                },
            )
            observability_store.record(method, path, response.status_code, (perf_counter() - start) * 1000)
            return response

    response = await call_next(request)
    observability_store.record(method, path, response.status_code, (perf_counter() - start) * 1000)
    return response


app.include_router(api_router)
register_exception_handlers(app)
