from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import AuthContext, require_user
from app.db.session import get_db
from app.schemas.family import (
    FamilyOverviewResponse,
    HouseholdCreateRequest,
    HouseholdGoalCreateRequest,
    HouseholdGoalResponse,
    HouseholdMemberAddRequest,
    HouseholdResponse,
)
from app.services.entitlements import require_premium_access
from app.services.family import add_member, create_goal, create_household, get_overview

router = APIRouter(prefix="/family", tags=["family"])


@router.post("/households", response_model=HouseholdResponse)
def create_family_household(
    payload: HouseholdCreateRequest,
    user: AuthContext = Depends(require_user),
    db: Session = Depends(get_db),
) -> HouseholdResponse:
    require_premium_access(db, user.user_id)
    result = create_household(db, user.user_id, payload.name)
    return HouseholdResponse.model_validate(result)


@router.post("/households/{household_id}/members", response_model=HouseholdResponse)
def add_family_member(
    household_id: int,
    payload: HouseholdMemberAddRequest,
    user: AuthContext = Depends(require_user),
    db: Session = Depends(get_db),
) -> HouseholdResponse:
    require_premium_access(db, user.user_id)
    result = add_member(db, household_id, user.user_id, payload)
    return HouseholdResponse.model_validate(result)


@router.post("/households/{household_id}/goals", response_model=HouseholdGoalResponse)
def add_family_goal(
    household_id: int,
    payload: HouseholdGoalCreateRequest,
    user: AuthContext = Depends(require_user),
    db: Session = Depends(get_db),
) -> HouseholdGoalResponse:
    require_premium_access(db, user.user_id)
    result = create_goal(db, household_id, user.user_id, payload)
    return HouseholdGoalResponse.model_validate(result)


@router.get("/overview", response_model=FamilyOverviewResponse)
def family_overview(
    household_id: int = Query(..., gt=0),
    user: AuthContext = Depends(require_user),
    db: Session = Depends(get_db),
) -> FamilyOverviewResponse:
    require_premium_access(db, user.user_id)
    result = get_overview(db, household_id, user.user_id)
    return FamilyOverviewResponse.model_validate(result)
