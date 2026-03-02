from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import AuthContext, require_admin
from app.db.session import get_db
from app.schemas.admin import (
    AIUsageResponse,
    AdminActionResponse,
    AdminOverviewResponse,
    DataHealthResponse,
    ObservabilityResponse,
    SubscriptionsResponse,
)
from app.services.admin import get_ai_usage, get_data_health, get_overview, list_subscriptions, reset_password, suspend_user
from app.core.observability import observability_store

router = APIRouter(prefix="/admin", tags=["admin"])


class SuspendUserRequest(BaseModel):
    reason: str | None = None


@router.get("/overview", response_model=AdminOverviewResponse)
def admin_overview(
    admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminOverviewResponse:
    _ = admin
    return AdminOverviewResponse.model_validate(get_overview(db))


@router.get("/subscriptions", response_model=SubscriptionsResponse)
def admin_subscriptions(
    admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SubscriptionsResponse:
    _ = admin
    return SubscriptionsResponse.model_validate(list_subscriptions(db))


@router.get("/ai-usage", response_model=AIUsageResponse)
def admin_ai_usage(
    admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AIUsageResponse:
    _ = admin
    return AIUsageResponse.model_validate(get_ai_usage(db))


@router.get("/data-health", response_model=DataHealthResponse)
def admin_data_health(
    admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> DataHealthResponse:
    _ = admin
    return DataHealthResponse.model_validate(get_data_health(db))


@router.get("/observability", response_model=ObservabilityResponse)
def admin_observability(
    admin: AuthContext = Depends(require_admin),
) -> ObservabilityResponse:
    _ = admin
    return ObservabilityResponse.model_validate(observability_store.snapshot())


@router.post("/users/{user_id}/suspend", response_model=AdminActionResponse)
def admin_suspend_user(
    user_id: str,
    payload: SuspendUserRequest,
    admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    response = suspend_user(db, admin.user_id, user_id, payload.reason)
    return AdminActionResponse.model_validate(response)


@router.post("/users/{user_id}/reset-password", response_model=AdminActionResponse)
def admin_reset_password(
    user_id: str,
    admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    response = reset_password(db, admin.user_id, user_id)
    return AdminActionResponse.model_validate(response)
