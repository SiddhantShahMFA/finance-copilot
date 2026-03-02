from typing import Literal

from pydantic import BaseModel, Field


class CopilotQueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    params: dict[str, float] = Field(default_factory=dict)


class CopilotQueryResponse(BaseModel):
    intent_id: str
    tier: Literal["free", "premium"]
    computed_metrics: dict[str, float | int | str | bool | None]
    risk_flags: list[str]
    tradeoffs: list[str]
    explanation: str
    explanation_source: Literal["openai", "fallback"]
    safety_note: str
