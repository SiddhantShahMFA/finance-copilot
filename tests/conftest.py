import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

os.environ["DATABASE_URL"] = "sqlite:///./test_finance_copilot.db"
os.environ["JWT_SECRET_KEY"] = "test-secret"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_ISSUER"] = "finance-copilot"
os.environ["JWT_AUDIENCE"] = "finance-copilot-client"
os.environ["JWKS_URL"] = ""
os.environ["RATE_LIMIT_ENABLED"] = "true"
os.environ["RATE_LIMIT_REQUESTS"] = "5"
os.environ["RATE_LIMIT_WINDOW_SECONDS"] = "60"
os.environ["RATE_LIMIT_PATH_PREFIXES"] = "/v1/copilot/query,/v1/simulations/run,/v1/family"

from app.core.config import get_settings

get_settings.cache_clear()

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app, rate_limiter
from app.core.observability import observability_store


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    rate_limiter.reset()
    observability_store.reset()
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def make_token():
    settings = get_settings()

    def _make(user_id: str = "user-1", role: str = "user") -> str:
        now = datetime.now(tz=timezone.utc)
        payload = {
            "sub": user_id,
            "user_id": user_id,
            "role": role,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    return _make


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
