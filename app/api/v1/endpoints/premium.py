from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import AuthContext, require_user
from app.db.session import get_db
from app.schemas.premium import (
    CashflowInsightsResponse,
    DebtInsightsResponse,
    GoalFeasibilityResponse,
    HealthScoreResponse,
    SimulationRequest,
    SimulationResponse,
)
from app.services.financial_snapshots import latest_snapshot
from app.services.premium_engines import (
    cashflow_insights,
    debt_insights,
    goal_feasibility,
    health_score,
    run_simulation,
)

router = APIRouter(tags=["premium"])


@router.get("/health-score", response_model=HealthScoreResponse)
def get_health_score(
    user: AuthContext = Depends(require_user),
    db: Session = Depends(get_db),
) -> HealthScoreResponse:
    snapshot = latest_snapshot(db, user.user_id)
    return HealthScoreResponse.model_validate(health_score(snapshot))


@router.get("/debt/insights", response_model=DebtInsightsResponse)
def get_debt_insights(
    user: AuthContext = Depends(require_user),
    db: Session = Depends(get_db),
) -> DebtInsightsResponse:
    snapshot = latest_snapshot(db, user.user_id)
    return DebtInsightsResponse.model_validate(debt_insights(snapshot))


@router.get("/cashflow/insights", response_model=CashflowInsightsResponse)
def get_cashflow_insights(
    user: AuthContext = Depends(require_user),
    db: Session = Depends(get_db),
) -> CashflowInsightsResponse:
    snapshot = latest_snapshot(db, user.user_id)
    return CashflowInsightsResponse.model_validate(cashflow_insights(snapshot))


@router.get("/goals/feasibility", response_model=GoalFeasibilityResponse)
def get_goal_feasibility(
    target_amount: float = Query(..., ge=0),
    current_savings: float = Query(..., ge=0),
    remaining_months: int = Query(..., gt=0),
    monthly_contribution: float = Query(..., ge=0),
    user: AuthContext = Depends(require_user),
    db: Session = Depends(get_db),
) -> GoalFeasibilityResponse:
    snapshot = latest_snapshot(db, user.user_id)
    output = goal_feasibility(
        snapshot=snapshot,
        target_amount=target_amount,
        current_savings=current_savings,
        remaining_months=remaining_months,
        monthly_contribution=monthly_contribution,
    )
    return GoalFeasibilityResponse.model_validate(output)


@router.post("/simulations/run", response_model=SimulationResponse)
def post_simulation_run(
    payload: SimulationRequest,
    user: AuthContext = Depends(require_user),
    db: Session = Depends(get_db),
) -> SimulationResponse:
    snapshot = latest_snapshot(db, user.user_id)
    output = run_simulation(snapshot, payload.scenario, payload.params)
    return SimulationResponse(scenario=payload.scenario, output=output)
