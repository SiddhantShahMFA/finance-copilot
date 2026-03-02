from typing import Literal

from pydantic import BaseModel, Field


class HealthScoreComponent(BaseModel):
    name: str
    score: float
    weight: int
    metric: float


class HealthScoreResponse(BaseModel):
    total_score: float
    score_band: Literal["excellent", "stable", "warning", "critical"]
    components: list[HealthScoreComponent]


class DebtInsightsResponse(BaseModel):
    emi_income_ratio: float
    credit_utilization: float
    stress_band: Literal["low", "moderate", "high"]
    overload_warning: bool
    max_additional_emi: float


class CashflowInsightsResponse(BaseModel):
    monthly_surplus: float
    savings_rate: float
    emergency_runway_months: float
    safe_discretionary_spend: float
    lifestyle_inflation_risk: bool


class GoalFeasibilityResponse(BaseModel):
    required_monthly_saving: float
    contribution_ratio: float
    confidence_band: Literal["high", "moderate", "at_risk"]
    projected_delay_months: int | None


ScenarioType = Literal["affordability_check", "income_shock", "sip_increase", "emi_risk"]


class SimulationRequest(BaseModel):
    scenario: ScenarioType
    params: dict[str, float] = Field(default_factory=dict)


class SimulationResponse(BaseModel):
    scenario: ScenarioType
    output: dict[str, float | str | bool | None]
