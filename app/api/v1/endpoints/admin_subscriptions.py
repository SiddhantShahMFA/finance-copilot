from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import AuthContext, require_admin
from app.db.session import get_db
from app.schemas.entitlement import EntitlementOut, EntitlementPatchRequest
from app.services.entitlements import patch_entitlement

router = APIRouter(prefix="/admin/subscriptions", tags=["admin"])


@router.patch("/{user_id}", response_model=EntitlementOut)
def admin_patch_subscription(
    user_id: str,
    payload: EntitlementPatchRequest,
    admin: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> EntitlementOut:
    entitlement = patch_entitlement(db, admin.user_id, user_id, payload)
    return EntitlementOut.model_validate(entitlement)
