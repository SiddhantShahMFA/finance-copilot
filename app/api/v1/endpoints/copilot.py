from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import AuthContext, require_user
from app.db.session import get_db
from app.schemas.copilot import CopilotQueryRequest, CopilotQueryResponse
from app.services.copilot import run_copilot_query

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.post("/query", response_model=CopilotQueryResponse)
def copilot_query(
    payload: CopilotQueryRequest,
    user: AuthContext = Depends(require_user),
    db: Session = Depends(get_db),
) -> CopilotQueryResponse:
    return run_copilot_query(db, user.user_id, payload.question, payload.params)
