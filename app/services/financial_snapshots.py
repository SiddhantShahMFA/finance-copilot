from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCodes
from app.db.models import FinancialSnapshot
from app.schemas.financial_snapshot import FinancialSnapshotIn


def upsert_snapshot(db: Session, user_id: str, payload: FinancialSnapshotIn) -> FinancialSnapshot:
    statement = select(FinancialSnapshot).where(
        FinancialSnapshot.user_id == user_id,
        FinancialSnapshot.month == payload.month,
    )
    snapshot = db.execute(statement).scalar_one_or_none()

    if not snapshot:
        snapshot = FinancialSnapshot(user_id=user_id, **payload.model_dump())
        db.add(snapshot)
    else:
        for field, value in payload.model_dump().items():
            setattr(snapshot, field, value)

    db.commit()
    db.refresh(snapshot)
    return snapshot


def latest_snapshot(db: Session, user_id: str) -> FinancialSnapshot:
    statement = (
        select(FinancialSnapshot)
        .where(FinancialSnapshot.user_id == user_id)
        .order_by(desc(FinancialSnapshot.month))
        .limit(1)
    )
    snapshot = db.execute(statement).scalar_one_or_none()
    if not snapshot:
        raise AppError(ErrorCodes.NOT_FOUND, "No financial snapshot found", status_code=404)
    return snapshot
