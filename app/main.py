from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging

settings = get_settings()

configure_logging()
app = FastAPI(title=settings.app_name, version=settings.api_version)
app.include_router(api_router)
register_exception_handlers(app)
