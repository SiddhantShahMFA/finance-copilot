from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import AIPromptLog, AccountLink, AdminAuditLog, FinancialSnapshot, UserEntitlement
from app.db.models.user_entitlement import EntitlementSourceEnum, EntitlementStatusEnum, PlanEnum


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _month_start_utc(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _current_month_date(now: datetime):
    return now.date().replace(day=1)


def _registered_user_ids(db: Session) -> set[str]:
    entitlement_ids = set(db.execute(select(UserEntitlement.user_id)).scalars().all())
    snapshot_ids = set(db.execute(select(FinancialSnapshot.user_id).distinct()).scalars().all())
    linked_ids = set(db.execute(select(AccountLink.user_id).distinct()).scalars().all())
    prompt_ids = set(db.execute(select(AIPromptLog.user_id).distinct()).scalars().all())
    return entitlement_ids | snapshot_ids | linked_ids | prompt_ids


def get_overview(db: Session) -> dict:
    now = _now_utc()
    month_start_ts = _month_start_utc(now)
    month_start_date = _current_month_date(now)

    registered_user_ids = _registered_user_ids(db)

    active_from_prompts = set(
        db.execute(select(AIPromptLog.user_id).where(AIPromptLog.created_at >= month_start_ts).distinct()).scalars().all()
    )
    active_from_snapshots = set(
        db.execute(
            select(FinancialSnapshot.user_id)
            .where(FinancialSnapshot.month == month_start_date)
            .distinct()
        ).scalars().all()
    )
    monthly_active_users = len(active_from_prompts | active_from_snapshots)

    premium_count = db.execute(
        select(func.count())
        .select_from(UserEntitlement)
        .where(UserEntitlement.plan == PlanEnum.premium, UserEntitlement.status == EntitlementStatusEnum.active)
    ).scalar_one()

    total_registered = len(registered_user_ids)
    conversion_rate = (float(premium_count) / total_registered * 100.0) if total_registered > 0 else 0.0

    return {
        "total_registered_users": total_registered,
        "monthly_active_users": monthly_active_users,
        "total_premium_users": int(premium_count),
        "conversion_rate": round(conversion_rate, 2),
    }


def list_subscriptions(db: Session) -> dict:
    user_ids = sorted(_registered_user_ids(db))
    entitlements = {
        item.user_id: item
        for item in db.execute(select(UserEntitlement)).scalars().all()
    }

    items = []
    for user_id in user_ids:
        ent = entitlements.get(user_id)
        if ent:
            plan = ent.plan.value
            status = ent.status.value
            start_date = ent.created_at
            expiry_date = ent.expiry_date
            source = ent.source.value
        else:
            plan = PlanEnum.free.value
            status = EntitlementStatusEnum.active.value
            start_date = None
            expiry_date = None
            source = EntitlementSourceEnum.manual.value

        payment_status = "paid" if plan == PlanEnum.premium.value and status == EntitlementStatusEnum.active.value else "n/a"

        items.append(
            {
                "user_id": user_id,
                "user_name": None,
                "contact": None,
                "plan": plan,
                "status": status,
                "start_date": start_date,
                "expiry_date": expiry_date,
                "payment_status": payment_status,
                "source": source,
            }
        )

    return {"items": items}


def get_ai_usage(db: Session) -> dict:
    total_prompts = db.execute(select(func.count()).select_from(AIPromptLog)).scalar_one()
    unique_users = db.execute(select(func.count(func.distinct(AIPromptLog.user_id)))).scalar_one()
    failed_prompts = db.execute(
        select(func.count()).select_from(AIPromptLog).where(AIPromptLog.status == "failed")
    ).scalar_one()

    top_rows = db.execute(
        select(AIPromptLog.question, func.count(AIPromptLog.id).label("c"))
        .group_by(AIPromptLog.question)
        .order_by(func.count(AIPromptLog.id).desc())
        .limit(5)
    ).all()

    return {
        "total_prompts_used": int(total_prompts),
        "avg_prompts_per_user": round((float(total_prompts) / unique_users) if unique_users > 0 else 0.0, 2),
        "top_asked_questions": [row[0] for row in top_rows],
        "failed_prompts": int(failed_prompts),
    }


def get_data_health(db: Session) -> dict:
    linked_bank_count = db.execute(
        select(func.count()).select_from(AccountLink).where(AccountLink.account_type == "bank", AccountLink.status == "linked")
    ).scalar_one()

    linked_mf_count = db.execute(
        select(func.count()).select_from(AccountLink).where(AccountLink.account_type == "mf", AccountLink.status == "linked")
    ).scalar_one()

    linked_stock_count = db.execute(
        select(func.count()).select_from(AccountLink).where(AccountLink.account_type == "stock", AccountLink.status == "linked")
    ).scalar_one()

    latest_asset_subq = (
        select(FinancialSnapshot.user_id, func.max(FinancialSnapshot.month).label("max_month"))
        .group_by(FinancialSnapshot.user_id)
        .subquery()
    )

    avg_assets = db.execute(
        select(func.avg(FinancialSnapshot.assets_total))
        .join(
            latest_asset_subq,
            (FinancialSnapshot.user_id == latest_asset_subq.c.user_id)
            & (FinancialSnapshot.month == latest_asset_subq.c.max_month),
        )
    ).scalar_one()

    return {
        "linked_bank_accounts_count": int(linked_bank_count),
        "linked_mf_count": int(linked_mf_count),
        "linked_stock_accounts_count": int(linked_stock_count),
        "avg_assets_per_user": round(float(avg_assets or 0.0), 2),
    }


def suspend_user(db: Session, actor_user_id: str, target_user_id: str, reason: str | None) -> dict:
    entitlement = db.get(UserEntitlement, target_user_id)
    if not entitlement:
        entitlement = UserEntitlement(
            user_id=target_user_id,
            plan=PlanEnum.free,
            status=EntitlementStatusEnum.inactive,
            source=EntitlementSourceEnum.manual,
        )
        db.add(entitlement)
    else:
        entitlement.status = EntitlementStatusEnum.inactive

    audit = AdminAuditLog(
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        action="SUSPEND_USER",
        payload_json={"reason": reason},
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "action": "SUSPEND_USER",
        "user_id": target_user_id,
        "message": "User suspended",
    }


def reset_password(db: Session, actor_user_id: str, target_user_id: str) -> dict:
    audit = AdminAuditLog(
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        action="RESET_PASSWORD_REQUESTED",
        payload_json={"note": "Password reset requested by admin"},
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "action": "RESET_PASSWORD_REQUESTED",
        "user_id": target_user_id,
        "message": "Password reset request recorded",
    }
