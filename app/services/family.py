from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCodes
from app.db.models import FinancialSnapshot, Household, HouseholdGoal, HouseholdMember
from app.schemas.family import HouseholdGoalCreateRequest, HouseholdMemberAddRequest
from app.services.premium_engines import health_score


def _household_or_404(db: Session, household_id: int) -> Household:
    household = db.get(Household, household_id)
    if not household:
        raise AppError(ErrorCodes.NOT_FOUND, "Household not found", status_code=404)
    return household


def _member_record(db: Session, household_id: int, user_id: str) -> HouseholdMember | None:
    return db.execute(
        select(HouseholdMember).where(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == user_id,
        )
    ).scalar_one_or_none()


def _ensure_owner(db: Session, household_id: int, actor_user_id: str) -> None:
    member = _member_record(db, household_id, actor_user_id)
    if not member or member.role != "owner":
        raise AppError(ErrorCodes.AUTH_FORBIDDEN, "Only household owner can perform this action", status_code=403)


def _ensure_member(db: Session, household_id: int, actor_user_id: str) -> None:
    member = _member_record(db, household_id, actor_user_id)
    if not member:
        raise AppError(ErrorCodes.AUTH_FORBIDDEN, "User is not a household member", status_code=403)


def create_household(db: Session, owner_user_id: str, name: str) -> dict:
    household = Household(name=name.strip(), owner_user_id=owner_user_id)
    db.add(household)
    db.flush()

    owner_member = HouseholdMember(household_id=household.id, user_id=owner_user_id, role="owner")
    db.add(owner_member)
    db.commit()
    db.refresh(household)

    return {
        "id": household.id,
        "name": household.name,
        "owner_user_id": household.owner_user_id,
        "member_count": 1,
    }


def add_member(db: Session, household_id: int, actor_user_id: str, payload: HouseholdMemberAddRequest) -> dict:
    _household_or_404(db, household_id)
    _ensure_owner(db, household_id, actor_user_id)

    existing = _member_record(db, household_id, payload.user_id)
    if existing:
        raise AppError(ErrorCodes.DB_CONFLICT, "Member already in household", status_code=409)

    member = HouseholdMember(household_id=household_id, user_id=payload.user_id, role=payload.role)
    db.add(member)
    db.commit()

    member_count = db.execute(
        select(func.count()).select_from(HouseholdMember).where(HouseholdMember.household_id == household_id)
    ).scalar_one()

    household = _household_or_404(db, household_id)
    return {
        "id": household.id,
        "name": household.name,
        "owner_user_id": household.owner_user_id,
        "member_count": int(member_count),
    }


def create_goal(db: Session, household_id: int, actor_user_id: str, payload: HouseholdGoalCreateRequest) -> dict:
    _household_or_404(db, household_id)
    _ensure_owner(db, household_id, actor_user_id)

    goal = HouseholdGoal(
        household_id=household_id,
        name=payload.name,
        target_amount=payload.target_amount,
        current_savings=payload.current_savings,
        remaining_months=payload.remaining_months,
        monthly_contribution=payload.monthly_contribution,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)

    return {
        "id": goal.id,
        "household_id": goal.household_id,
        "name": goal.name,
        "target_amount": float(goal.target_amount),
        "current_savings": float(goal.current_savings),
        "remaining_months": goal.remaining_months,
        "monthly_contribution": float(goal.monthly_contribution),
    }


def get_overview(db: Session, household_id: int, actor_user_id: str) -> dict:
    _household_or_404(db, household_id)
    _ensure_member(db, household_id, actor_user_id)

    members = db.execute(
        select(HouseholdMember).where(HouseholdMember.household_id == household_id)
    ).scalars().all()
    member_user_ids = [m.user_id for m in members]

    latest_snapshot_subq = (
        select(FinancialSnapshot.user_id, func.max(FinancialSnapshot.month).label("max_month"))
        .where(FinancialSnapshot.user_id.in_(member_user_ids))
        .group_by(FinancialSnapshot.user_id)
        .subquery()
    )

    snapshots = db.execute(
        select(FinancialSnapshot)
        .join(
            latest_snapshot_subq,
            (FinancialSnapshot.user_id == latest_snapshot_subq.c.user_id)
            & (FinancialSnapshot.month == latest_snapshot_subq.c.max_month),
        )
        .order_by(desc(FinancialSnapshot.user_id))
    ).scalars().all()

    by_user = {s.user_id: s for s in snapshots}

    contributions: list[dict] = []
    shared_net_worth = 0.0
    score_values: list[float] = []

    for user_id in member_user_ids:
        snapshot = by_user.get(user_id)
        if snapshot:
            net_worth = float(snapshot.assets_total) - float(snapshot.liabilities_total)
            monthly_surplus = float(snapshot.income_total) - float(snapshot.expense_total)
            user_score = float(health_score(snapshot)["total_score"])
        else:
            net_worth = 0.0
            monthly_surplus = 0.0
            user_score = 0.0

        contributions.append(
            {
                "user_id": user_id,
                "net_worth": round(net_worth, 2),
                "monthly_surplus": round(monthly_surplus, 2),
                "health_score": round(user_score, 2),
            }
        )
        shared_net_worth += net_worth
        score_values.append(user_score)

    goals = db.execute(
        select(HouseholdGoal).where(HouseholdGoal.household_id == household_id)
    ).scalars().all()

    combined_goal_target = sum(float(g.target_amount) for g in goals)
    combined_goal_current_savings = sum(float(g.current_savings) for g in goals)
    combined_required_monthly_saving = 0.0
    for goal in goals:
        remaining = max(float(goal.target_amount) - float(goal.current_savings), 0.0)
        combined_required_monthly_saving += (remaining / goal.remaining_months) if goal.remaining_months > 0 else 0.0

    family_score = (sum(score_values) / len(score_values)) if score_values else 0.0

    return {
        "household_id": household_id,
        "shared_net_worth": round(shared_net_worth, 2),
        "combined_goal_target": round(combined_goal_target, 2),
        "combined_goal_current_savings": round(combined_goal_current_savings, 2),
        "combined_required_monthly_saving": round(combined_required_monthly_saving, 2),
        "family_health_score": round(family_score, 2),
        "contribution_breakdown": contributions,
    }
