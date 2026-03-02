from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCodes
from app.db.models import (
    AdminAuditLog,
    EntitlementSourceEnum,
    EntitlementStatusEnum,
    PlanEnum,
    UserEntitlement,
)
from app.schemas.entitlement import EntitlementPatchRequest


def _validate_plan(plan: str) -> PlanEnum:
    try:
        return PlanEnum(plan)
    except ValueError as exc:
        raise AppError(ErrorCodes.VALIDATION_ERROR, "Invalid plan value", status_code=422) from exc


def _validate_status(status: str) -> EntitlementStatusEnum:
    try:
        return EntitlementStatusEnum(status)
    except ValueError as exc:
        raise AppError(ErrorCodes.VALIDATION_ERROR, "Invalid status value", status_code=422) from exc


def get_or_create_entitlement(db: Session, user_id: str) -> UserEntitlement:
    entitlement = db.get(UserEntitlement, user_id)
    if entitlement:
        return entitlement

    entitlement = UserEntitlement(
        user_id=user_id,
        plan=PlanEnum.free,
        status=EntitlementStatusEnum.active,
        source=EntitlementSourceEnum.manual,
    )
    db.add(entitlement)
    db.commit()
    db.refresh(entitlement)
    return entitlement


def has_premium_access(entitlement: UserEntitlement) -> bool:
    if entitlement.plan != PlanEnum.premium or entitlement.status != EntitlementStatusEnum.active:
        return False

    if entitlement.expiry_date:
        expiry = entitlement.expiry_date
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        else:
            expiry = expiry.astimezone(timezone.utc)
        if expiry < datetime.now(timezone.utc):
            return False

    return True


def require_premium_access(db: Session, user_id: str) -> UserEntitlement:
    entitlement = get_or_create_entitlement(db, user_id)
    if not has_premium_access(entitlement):
        raise AppError(
            ErrorCodes.ENTITLEMENT_REQUIRED,
            "Premium plan required for this endpoint",
            status_code=403,
        )
    return entitlement


def patch_entitlement(
    db: Session,
    actor_user_id: str,
    target_user_id: str,
    patch: EntitlementPatchRequest,
) -> UserEntitlement:
    entitlement = db.get(UserEntitlement, target_user_id)
    if not entitlement:
        entitlement = UserEntitlement(
            user_id=target_user_id,
            plan=PlanEnum.free,
            status=EntitlementStatusEnum.active,
            source=EntitlementSourceEnum.manual,
        )
        db.add(entitlement)

    entitlement.plan = _validate_plan(patch.plan)
    entitlement.status = _validate_status(patch.status)
    entitlement.source = EntitlementSourceEnum.manual
    entitlement.expiry_date = patch.expiry_date

    audit = AdminAuditLog(
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        action="PATCH_SUBSCRIPTION",
        payload_json={
            "plan": patch.plan,
            "status": patch.status,
            "expiry_date": patch.expiry_date.isoformat() if patch.expiry_date else None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    db.add(audit)

    db.commit()
    db.refresh(entitlement)
    return entitlement
