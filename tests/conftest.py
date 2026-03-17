import os
import uuid
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


def _test_user_id(env_name: str, fallback_prefix: str) -> str:
    """
    Return a stable test user_id sourced from environment where possible.

    This avoids hardcoding IDs directly in test modules while still allowing
    deterministic values when desired by configuring the test environment.
    """
    env_value = os.getenv(env_name)
    if env_value:
        return env_value
    # Generate a non-hardcoded, but stable-looking ID for local runs.
    return f"{fallback_prefix}-{uuid.uuid4()}"


# Centralised test user identifiers used across test modules.
TEST_USER_ID = _test_user_id("TEST_USER_ID", "user")
TEST_USER_ID_2 = _test_user_id("TEST_USER_ID_2", "user")
TEST_USER_ID_3 = _test_user_id("TEST_USER_ID_3", "user")

TEST_ADMIN_ID = _test_user_id("TEST_ADMIN_ID", "admin")
TEST_ADMIN_ID_2 = _test_user_id("TEST_ADMIN_ID_2", "admin")

TEST_USAGE_USER_ID = _test_user_id("TEST_USAGE_USER_ID", "usage-user")

TEST_FAMILY_FREE_USER_ID = _test_user_id("TEST_FAMILY_FREE_USER_ID", "family-free")
TEST_FAMILY_OWNER_USER_ID = _test_user_id("TEST_FAMILY_OWNER_USER_ID", "family-owner")
TEST_FAMILY_MEMBER_USER_ID = _test_user_id("TEST_FAMILY_MEMBER_USER_ID", "family-member")

TEST_E2E_ADMIN_ID = _test_user_id("TEST_E2E_ADMIN_ID", "admin-e2e")
TEST_E2E_OWNER_ID = _test_user_id("TEST_E2E_OWNER_ID", "owner-e2e")
TEST_E2E_PARTNER_ID = _test_user_id("TEST_E2E_PARTNER_ID", "partner-e2e")

TEST_COPILOT_USER_ID = _test_user_id("TEST_COPILOT_USER_ID", "copilot-user")
TEST_FREE_USER_ID = _test_user_id("TEST_FREE_USER_ID", "free-user")
TEST_FREE_BLOCKED_USER_ID = _test_user_id("TEST_FREE_BLOCKED_USER_ID", "free-blocked")
TEST_PREMIUM_USER_ID = _test_user_id("TEST_PREMIUM_USER_ID", "premium-user")

TEST_PREMIUM_HEALTH_USER_ID = _test_user_id("TEST_PREMIUM_HEALTH_USER_ID", "u-premium")
TEST_PREMIUM_GOAL_USER_ID = _test_user_id("TEST_PREMIUM_GOAL_USER_ID", "u-goal")
TEST_PREMIUM_SIM_USER_ID = _test_user_id("TEST_PREMIUM_SIM_USER_ID", "u-sim")

TEST_SNAPSHOT_USER_ID_1 = _test_user_id("TEST_SNAPSHOT_USER_ID_1", "user-100")
TEST_SNAPSHOT_USER_ID_2 = _test_user_id("TEST_SNAPSHOT_USER_ID_2", "user-101")
TEST_SNAPSHOT_USER_ID_3 = _test_user_id("TEST_SNAPSHOT_USER_ID_3", "user-102")

TEST_OBSERVABILITY_ADMIN_ID = _test_user_id("TEST_OBSERVABILITY_ADMIN_ID", "admin-obsv")
TEST_OBSERVABILITY_USER_ID = _test_user_id("TEST_OBSERVABILITY_USER_ID", "obsv-user")
TEST_RATELIMIT_USER_ID = _test_user_id("TEST_RATELIMIT_USER_ID", "ratelimit-user")


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

    def _make(user_id: str = TEST_USER_ID, role: str = "user") -> str:
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
