from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import AuthContext, require_user
from app.db.session import get_db
from app.schemas.financial_snapshot import FinancialSnapshotIn, FinancialSnapshotOut
from app.services.financial_snapshots import latest_snapshot, upsert_snapshot

router = APIRouter(prefix="/financial-snapshots", tags=["financial_snapshots"])


@router.post("", response_model=FinancialSnapshotOut)
def create_or_update_snapshot(
    payload: FinancialSnapshotIn,
    user: AuthContext = Depends(require_user),
    db: Session = Depends(get_db),
) -> FinancialSnapshotOut:
    snapshot = upsert_snapshot(db, user.user_id, payload)
    return FinancialSnapshotOut.model_validate(snapshot)


@router.get("/latest", response_model=FinancialSnapshotOut)
def get_latest_snapshot(
    user: AuthContext = Depends(require_user),
    db: Session = Depends(get_db),
) -> FinancialSnapshotOut:
    snapshot = latest_snapshot(db, user.user_id)
    return FinancialSnapshotOut.model_validate(snapshot)
