from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import AuthContext, require_user
from app.db.session import get_db
from app.schemas.entitlement import EntitlementOut
from app.services.entitlements import get_or_create_entitlement

router = APIRouter(prefix="/entitlement", tags=["entitlements"])


@router.get("/me", response_model=EntitlementOut)
def entitlement_me(
    user: AuthContext = Depends(require_user),
    db: Session = Depends(get_db),
) -> EntitlementOut:
    entitlement = get_or_create_entitlement(db, user.user_id)
    return EntitlementOut.model_validate(entitlement)
