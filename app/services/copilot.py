import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCodes
from app.db.models import FinancialSnapshot
from app.schemas.copilot import CopilotQueryResponse
from app.services.ai_explainer import SAFETY_NOTE, generate_explanation
from app.services.entitlements import get_or_create_entitlement
from app.services.financial_snapshots import latest_snapshot
from app.services.intent_router import resolve_intent
from app.services.premium_engines import cashflow_insights, debt_insights, goal_feasibility, health_score, run_simulation


def _extract_first_number(text: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)", text.replace(",", ""))
    return float(match.group(1)) if match else None


def _as_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _has_premium_access(entitlement) -> bool:
    if entitlement.plan.value != "premium" or entitlement.status.value != "active":
        return False
    expiry = _as_utc(entitlement.expiry_date)
    if expiry and expiry < datetime.now(timezone.utc):
        return False
    return True


def _require_param(params: dict[str, float], key: str, fallback: float | None = None) -> float:
    value = params.get(key)
    if value is not None:
        return float(value)
    if fallback is not None:
        return float(fallback)
    raise AppError(ErrorCodes.VALIDATION_ERROR, f"Missing required parameter: {key}", status_code=422)


def _build_response(
    intent_id: str,
    tier: str,
    metrics: dict,
    risk_flags: list[str],
    tradeoffs: list[str],
) -> CopilotQueryResponse:
    explanation, source = generate_explanation(intent_id, metrics, risk_flags, tradeoffs)
    return CopilotQueryResponse(
        intent_id=intent_id,
        tier=tier,
        computed_metrics=metrics,
        risk_flags=risk_flags,
        tradeoffs=tradeoffs,
        explanation=explanation,
        explanation_source=source,
        safety_note=SAFETY_NOTE,
    )


def _handle_free_intent(snapshot: FinancialSnapshot, intent_id: str) -> tuple[dict, list[str], list[str]]:
    if intent_id == "overspending_summary":
        income = float(snapshot.income_total)
        if income <= 0:
            spend_ratio = float('inf') if float(snapshot.expense_total) > 0 else 0.0
        else:
            spend_ratio = float(snapshot.expense_total) / income
        metrics = {
            "monthly_expense": round(float(snapshot.expense_total), 2),
            "expense_to_income_ratio": round(spend_ratio, 4),
            "overspending": spend_ratio > 1,
        }
        risks = ["overspending_detected"] if spend_ratio > 1 else []
        tradeoffs = ["Higher spending reduces monthly savings capacity"]
        return metrics, risks, tradeoffs

    if intent_id == "savings_rate_summary":
        cf = cashflow_insights(snapshot)
        metrics = {
            "savings_rate": cf["savings_rate"],
            "monthly_surplus": cf["monthly_surplus"],
        }
        risks = ["low_savings_rate"] if cf["savings_rate"] < 0.15 else []
        tradeoffs = ["Increasing savings rate may reduce discretionary spending"]
        return metrics, risks, tradeoffs

    if intent_id == "monthly_spend_summary":
        metrics = {
            "monthly_spend": round(float(snapshot.expense_total), 2),
            "emi_total": round(float(snapshot.emi_total), 2),
        }
        risks = ["high_fixed_commitments"] if float(snapshot.emi_total) > (0.4 * float(snapshot.income_total)) else []
        tradeoffs = ["Higher EMI obligations shrink spend flexibility"]
        return metrics, risks, tradeoffs

    raise AppError(ErrorCodes.VALIDATION_ERROR, "Unsupported free intent", status_code=422)


def _handle_premium_intent(snapshot: FinancialSnapshot, intent_id: str, question: str, params: dict[str, float]) -> tuple[dict, list[str], list[str]]:
    if intent_id == "affordability_check":
        purchase_amount = params.get("purchase_amount")
        if purchase_amount is None:
            purchase_amount = _extract_first_number(question)
        if purchase_amount is None:
            raise AppError(ErrorCodes.VALIDATION_ERROR, "Missing purchase_amount", status_code=422)

        result = run_simulation(
            snapshot,
            "affordability_check",
            {
                "purchase_amount": float(purchase_amount),
                "upfront_ratio": float(params.get("upfront_ratio", 0.2)),
                "tenure_months": float(params.get("tenure_months", 24)),
            },
        )
        risks = ["high_emi_pressure"] if result["projected_emi_income_ratio"] > 0.4 else []
        tradeoffs = ["Higher upfront payment improves EMI sustainability"]
        return result, risks, tradeoffs

    if intent_id == "lifestyle_inflation_detection":
        cf = cashflow_insights(snapshot)
        spend_income = round(float(snapshot.expense_total) / max(float(snapshot.income_total), 1), 4)
        metrics = {
            "expense_to_income_ratio": spend_income,
            "savings_rate": cf["savings_rate"],
            "lifestyle_inflation_risk": cf["lifestyle_inflation_risk"],
        }
        risks = ["lifestyle_inflation_risk"] if cf["lifestyle_inflation_risk"] else []
        tradeoffs = ["Reducing discretionary expense improves long-term savings runway"]
        return metrics, risks, tradeoffs

    if intent_id == "sip_increase":
        increase_amount = params.get("increase_amount")
        if increase_amount is None:
            increase_amount = _extract_first_number(question)
        if increase_amount is None:
            raise AppError(ErrorCodes.VALIDATION_ERROR, "Missing increase_amount", status_code=422)

        result = run_simulation(snapshot, "sip_increase", {"increase_amount": float(increase_amount)})
        risks = ["emergency_buffer_pressure"] if result["emergency_runway_months"] < 4 else []
        tradeoffs = ["Higher SIP contribution can reduce short-term liquidity"]
        return result, risks, tradeoffs

    if intent_id == "goal_feasibility_check":
        result = goal_feasibility(
            snapshot,
            target_amount=_require_param(params, "target_amount"),
            current_savings=_require_param(params, "current_savings", 0.0),
            remaining_months=int(_require_param(params, "remaining_months")),
            monthly_contribution=_require_param(params, "monthly_contribution"),
        )
        risks = ["goal_at_risk"] if result["confidence_band"] == "at_risk" else []
        tradeoffs = ["Increasing monthly contribution may require expense cuts"]
        return result, risks, tradeoffs

    if intent_id == "goal_conflict_detection":
        goal_a = _require_param(params, "goal_a_monthly")
        goal_b = _require_param(params, "goal_b_monthly")
        surplus = float(snapshot.income_total) - float(snapshot.expense_total)
        overlap = (goal_a + goal_b) > surplus
        metrics = {
            "monthly_surplus": round(surplus, 2),
            "combined_goal_monthly_need": round(goal_a + goal_b, 2),
            "goal_conflict": overlap,
        }
        risks = ["cashflow_goal_conflict"] if overlap else []
        tradeoffs = ["Parallel goals accelerate outcomes but increase monthly cash strain"]
        return metrics, risks, tradeoffs

    if intent_id == "delay_impact_analysis":
        target_amount = _require_param(params, "target_amount")
        current_savings = _require_param(params, "current_savings", 0.0)
        remaining_months = int(_require_param(params, "remaining_months"))
        monthly_contribution = _require_param(params, "monthly_contribution")
        delay_months = int(_require_param(params, "delay_months", 12))

        current_plan = goal_feasibility(snapshot, target_amount, current_savings, remaining_months, monthly_contribution)
        delayed_plan = goal_feasibility(
            snapshot,
            target_amount,
            current_savings,
            remaining_months + delay_months,
            monthly_contribution,
        )
        metrics = {
            "current_required_monthly": current_plan["required_monthly_saving"],
            "delayed_required_monthly": delayed_plan["required_monthly_saving"],
            "delay_months": delay_months,
        }
        risks = [] if delayed_plan["confidence_band"] != "at_risk" else ["goal_still_at_risk"]
        tradeoffs = ["Delaying goals lowers monthly burden but postpones goal completion"]
        return metrics, risks, tradeoffs

    if intent_id == "debt_stress_analysis":
        result = debt_insights(snapshot)
        risks = ["high_debt_stress"] if result["stress_band"] == "high" else []
        tradeoffs = ["Aggressive debt repayment improves risk score but reduces free cash flow"]
        return result, risks, tradeoffs

    if intent_id == "emi_overload_warning":
        additional_emi = params.get("additional_emi")
        if additional_emi is None:
            additional_emi = _extract_first_number(question)
        if additional_emi is None:
            raise AppError(ErrorCodes.VALIDATION_ERROR, "Missing additional_emi", status_code=422)

        result = run_simulation(snapshot, "emi_risk", {"additional_emi": float(additional_emi)})
        risks = ["emi_overload"] if result["high_risk"] else []
        tradeoffs = ["New EMI increases affordability risk for goals and emergency reserve"]
        return result, risks, tradeoffs

    if intent_id == "credit_card_behavior":
        result = debt_insights(snapshot)
        behavior = "healthy" if result["credit_utilization"] < 0.3 else "needs_attention"
        metrics = {
            "credit_utilization": result["credit_utilization"],
            "behavior": behavior,
        }
        risks = ["high_credit_utilization"] if result["credit_utilization"] > 0.5 else []
        tradeoffs = ["Lower card utilization may reduce short-term spending flexibility"]
        return metrics, risks, tradeoffs

    if intent_id == "subscription_leak_detection":
        cf = cashflow_insights(snapshot)
        leak_estimate = round(float(snapshot.expense_total) * 0.03, 2)
        metrics = {
            "estimated_monthly_leak": leak_estimate,
            "lifestyle_inflation_risk": cf["lifestyle_inflation_risk"],
        }
        risks = ["potential_subscription_leak"] if leak_estimate > 0 else []
        tradeoffs = ["Cutting recurring expenses increases surplus but may reduce convenience"]
        return metrics, risks, tradeoffs

    if intent_id == "safe_spend_limit":
        cf = cashflow_insights(snapshot)
        metrics = {
            "safe_discretionary_spend": cf["safe_discretionary_spend"],
            "monthly_surplus": cf["monthly_surplus"],
        }
        risks = ["limited_spending_room"] if cf["safe_discretionary_spend"] < 5000 else []
        tradeoffs = ["Higher discretionary spend reduces investable surplus"]
        return metrics, risks, tradeoffs

    if intent_id == "income_shock_simulation":
        drop_percent = params.get("drop_percent")
        if drop_percent is None:
            drop_percent = _extract_first_number(question) or 20
        result = run_simulation(snapshot, "income_shock", {"drop_percent": float(drop_percent)})
        risks = ["negative_monthly_surplus"] if result["risk_alert"] else []
        tradeoffs = ["Maintaining current expenses during income shock can erode reserves"]
        return result, risks, tradeoffs

    if intent_id == "family_readiness_check":
        cf = cashflow_insights(snapshot)
        debt = debt_insights(snapshot)
        ready = cf["emergency_runway_months"] >= 6 and debt["emi_income_ratio"] < 0.35
        metrics = {
            "family_readiness": ready,
            "emergency_runway_months": cf["emergency_runway_months"],
            "emi_income_ratio": debt["emi_income_ratio"],
        }
        risks = [] if ready else ["insufficient_family_buffer"]
        tradeoffs = ["Family planning needs stronger emergency runway and debt headroom"]
        return metrics, risks, tradeoffs

    if intent_id == "long_term_trajectory":
        years = int(_require_param(params, "years", 10))
        annual_return = _require_param(params, "annual_return", 0.10)
        current_net_worth = float(snapshot.assets_total) - float(snapshot.liabilities_total)
        monthly_surplus = float(snapshot.income_total) - float(snapshot.expense_total)
        future_value_lump = current_net_worth * ((1 + annual_return) ** years)
        if annual_return > 0:
            future_value_stream = monthly_surplus * 12 * (((1 + annual_return) ** years - 1) / annual_return)
        else:
            future_value_stream = monthly_surplus * 12 * years
        projected = future_value_lump + future_value_stream

        metrics = {
            "current_net_worth": round(current_net_worth, 2),
            "projected_net_worth": round(projected, 2),
            "years": years,
            "annual_return_assumption": annual_return,
        }
        risks = ["negative_projection"] if projected < current_net_worth else []
        tradeoffs = ["Higher return assumptions increase uncertainty in long-term projection"]
        return metrics, risks, tradeoffs

    if intent_id == "annual_review":
        score = health_score(snapshot)
        debt = debt_insights(snapshot)
        cf = cashflow_insights(snapshot)
        metrics = {
            "health_score": score["total_score"],
            "debt_stress_band": debt["stress_band"],
            "savings_rate": cf["savings_rate"],
        }
        priorities = []
        if cf["savings_rate"] < 0.15:
            priorities.append("Increase savings rate to at least 15% of income")
        if debt["emi_income_ratio"] > 0.40:
            priorities.append("Reduce EMI obligations below 40% of income")
        if cf["emergency_runway_months"] < 6:
            priorities.append("Build emergency runway to 6 months")
        if not priorities:
            priorities.append("Maintain current discipline and review quarterly")

        metrics["priority_actions_count"] = len(priorities)
        risks = ["annual_risk_flags_present"] if len(priorities) > 1 else []
        tradeoffs = priorities
        return metrics, risks, tradeoffs

    raise AppError(ErrorCodes.VALIDATION_ERROR, "Unsupported premium intent", status_code=422)


def run_copilot_query(db: Session, user_id: str, question: str, params: dict[str, float]) -> CopilotQueryResponse:
    intent = resolve_intent(question)
    snapshot = latest_snapshot(db, user_id)

    if intent.tier == "premium":
        entitlement = get_or_create_entitlement(db, user_id)
        if not _has_premium_access(entitlement):
            raise AppError(
                ErrorCodes.ENTITLEMENT_REQUIRED,
                "Premium plan required for this copilot intent",
                status_code=403,
            )

    if intent.tier == "free":
        metrics, risks, tradeoffs = _handle_free_intent(snapshot, intent.intent_id)
    else:
        metrics, risks, tradeoffs = _handle_premium_intent(snapshot, intent.intent_id, question, params)

    return _build_response(intent.intent_id, intent.tier, metrics, risks, tradeoffs)
