from sqlalchemy.orm import Session

from app.db.models import AIPromptLog


def log_prompt_usage(
    db: Session,
    user_id: str,
    question: str,
    status: str,
    intent_id: str | None = None,
    tier: str | None = None,
    error_code: str | None = None,
) -> None:
    record = AIPromptLog(
        user_id=user_id,
        question=question[:1024],
        intent_id=intent_id,
        tier=tier,
        status=status,
        error_code=error_code,
    )
    db.add(record)
    db.commit()
