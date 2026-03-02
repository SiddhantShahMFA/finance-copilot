import math

from app.core.errors import AppError, ErrorCodes
from app.db.models import FinancialSnapshot


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def debt_insights(snapshot: FinancialSnapshot) -> dict:
    emi_income_ratio = _safe_div(snapshot.emi_total, snapshot.income_total)
    credit_utilization = _safe_div(snapshot.credit_outstanding_total, snapshot.credit_limit_total)

    if emi_income_ratio > 0.40 or credit_utilization > 0.70:
        stress_band = "high"
    elif emi_income_ratio > 0.25 or credit_utilization > 0.40:
        stress_band = "moderate"
    else:
        stress_band = "low"

    max_additional_emi = max(float(snapshot.income_total) * 0.40 - float(snapshot.emi_total), 0.0)

    return {
        "emi_income_ratio": round(emi_income_ratio, 4),
        "credit_utilization": round(credit_utilization, 4),
        "stress_band": stress_band,
        "overload_warning": emi_income_ratio > 0.40,
        "max_additional_emi": round(max_additional_emi, 2),
    }


def cashflow_insights(snapshot: FinancialSnapshot) -> dict:
    monthly_surplus = float(snapshot.income_total) - float(snapshot.expense_total)
    savings_rate = _safe_div(monthly_surplus, snapshot.income_total)
    emergency_runway_months = _safe_div(snapshot.liquid_assets, snapshot.essential_expense)

    safe_discretionary_spend = max(monthly_surplus * 0.5, 0.0)
    lifestyle_inflation_risk = savings_rate < 0.15 and _safe_div(snapshot.expense_total, snapshot.income_total) > 0.80

    return {
        "monthly_surplus": round(monthly_surplus, 2),
        "savings_rate": round(savings_rate, 4),
        "emergency_runway_months": round(emergency_runway_months, 2),
        "safe_discretionary_spend": round(safe_discretionary_spend, 2),
        "lifestyle_inflation_risk": lifestyle_inflation_risk,
    }


def goal_feasibility(
    snapshot: FinancialSnapshot,
    target_amount: float,
    current_savings: float,
    remaining_months: int,
    monthly_contribution: float,
) -> dict:
    if target_amount < 0 or current_savings < 0 or monthly_contribution < 0 or remaining_months <= 0:
        raise AppError(
            ErrorCodes.VALIDATION_ERROR,
            "Invalid goal inputs. Ensure non-negative amounts and remaining_months > 0",
            status_code=422,
        )

    remaining_goal = max(target_amount - current_savings, 0.0)
    required_monthly = remaining_goal / remaining_months

    if required_monthly == 0:
        ratio = 1.0
    else:
        ratio = monthly_contribution / required_monthly

    if monthly_contribution <= 0 and remaining_goal > 0:
        projected_delay_months = None
    elif remaining_goal == 0:
        projected_delay_months = 0
    else:
        projected_total_months = math.ceil(remaining_goal / monthly_contribution)
        projected_delay_months = max(projected_total_months - remaining_months, 0)

    if ratio >= 1.1:
        confidence = "high"
    elif ratio >= 0.85:
        confidence = "moderate"
    else:
        confidence = "at_risk"

    if confidence == "high" and float(snapshot.emi_total) / max(float(snapshot.income_total), 1) > 0.4:
        confidence = "moderate"

    return {
        "required_monthly_saving": round(required_monthly, 2),
        "contribution_ratio": round(ratio, 3),
        "confidence_band": confidence,
        "projected_delay_months": projected_delay_months,
    }


def health_score(snapshot: FinancialSnapshot) -> dict:
    monthly_surplus = float(snapshot.income_total) - float(snapshot.expense_total)
    savings_rate = _safe_div(monthly_surplus, snapshot.income_total)
    emergency_months = _safe_div(snapshot.liquid_assets, snapshot.essential_expense)
    emi_ratio = _safe_div(snapshot.emi_total, snapshot.income_total)
    credit_utilization = _safe_div(snapshot.credit_outstanding_total, snapshot.credit_limit_total)

    savings_component = _clamp(savings_rate / 0.30) * 25
    emergency_component = _clamp(emergency_months / 6.0) * 20
    debt_component = _clamp((0.50 - emi_ratio) / 0.50) * 20
    credit_component = _clamp((0.80 - credit_utilization) / 0.80) * 15

    if savings_rate >= 0.20:
        goal_component = 20
    elif savings_rate >= 0.10:
        goal_component = 14
    elif savings_rate >= 0.05:
        goal_component = 8
    else:
        goal_component = 3

    total = savings_component + emergency_component + debt_component + credit_component + goal_component
    total = round(total, 2)

    if total >= 80:
        band = "excellent"
    elif total >= 60:
        band = "stable"
    elif total >= 40:
        band = "warning"
    else:
        band = "critical"

    return {
        "total_score": total,
        "score_band": band,
        "components": [
            {
                "name": "savings_rate",
                "score": round(savings_component, 2),
                "weight": 25,
                "metric": round(savings_rate, 4),
            },
            {
                "name": "emergency_adequacy",
                "score": round(emergency_component, 2),
                "weight": 20,
                "metric": round(emergency_months, 2),
            },
            {
                "name": "debt_stress",
                "score": round(debt_component, 2),
                "weight": 20,
                "metric": round(emi_ratio, 4),
            },
            {
                "name": "credit_utilization",
                "score": round(credit_component, 2),
                "weight": 15,
                "metric": round(credit_utilization, 4),
            },
            {
                "name": "goal_feasibility_proxy",
                "score": float(goal_component),
                "weight": 20,
                "metric": round(savings_rate, 4),
            },
        ],
    }


def run_simulation(snapshot: FinancialSnapshot, scenario: str, params: dict[str, float]) -> dict:
    income = float(snapshot.income_total)
    expense = float(snapshot.expense_total)
    liquid_assets = float(snapshot.liquid_assets)
    emi_total = float(snapshot.emi_total)
    essential_expense = float(snapshot.essential_expense)

    if scenario == "affordability_check":
        purchase_amount = float(params.get("purchase_amount", 0))
        upfront_ratio = float(params.get("upfront_ratio", 0.20))
        tenure_months = int(params.get("tenure_months", 24))
        if purchase_amount <= 0 or tenure_months <= 0 or upfront_ratio < 0 or upfront_ratio > 1:
            raise AppError(ErrorCodes.VALIDATION_ERROR, "Invalid affordability simulation inputs", status_code=422)

        upfront_needed = purchase_amount * upfront_ratio
        financed = max(purchase_amount - upfront_needed, 0)
        added_emi = financed / tenure_months
        projected_emi_ratio = _safe_div(emi_total + added_emi, income)

        if projected_emi_ratio <= 0.35 and upfront_needed <= liquid_assets * 0.5:
            decision = "yes"
        elif projected_emi_ratio <= 0.40:
            decision = "conditional_yes"
        else:
            decision = "no"

        return {
            "decision": decision,
            "upfront_needed": round(upfront_needed, 2),
            "projected_additional_emi": round(added_emi, 2),
            "projected_emi_income_ratio": round(projected_emi_ratio, 4),
        }

    if scenario == "income_shock":
        drop_percent = float(params.get("drop_percent", 20))
        if drop_percent < 0 or drop_percent > 90:
            raise AppError(ErrorCodes.VALIDATION_ERROR, "Invalid drop_percent", status_code=422)

        new_income = income * (1 - (drop_percent / 100))
        new_surplus = new_income - expense
        emergency_runway_months = _safe_div(liquid_assets, essential_expense)

        return {
            "new_income": round(new_income, 2),
            "new_monthly_surplus": round(new_surplus, 2),
            "emergency_runway_months": round(emergency_runway_months, 2),
            "risk_alert": new_surplus < 0,
        }

    if scenario == "sip_increase":
        increase_amount = float(params.get("increase_amount", 0))
        if increase_amount <= 0:
            raise AppError(ErrorCodes.VALIDATION_ERROR, "increase_amount must be > 0", status_code=422)

        monthly_surplus = income - expense
        emergency_runway_months = _safe_div(liquid_assets, essential_expense)
        safe_increment = max(monthly_surplus * 0.7, 0)
        feasible = increase_amount <= safe_increment and emergency_runway_months >= 4

        return {
            "requested_increment": round(increase_amount, 2),
            "safe_increment": round(safe_increment, 2),
            "feasible": feasible,
            "emergency_runway_months": round(emergency_runway_months, 2),
        }

    if scenario == "emi_risk":
        additional_emi = float(params.get("additional_emi", 0))
        if additional_emi <= 0:
            raise AppError(ErrorCodes.VALIDATION_ERROR, "additional_emi must be > 0", status_code=422)

        new_ratio = _safe_div(emi_total + additional_emi, income)
        return {
            "projected_emi_income_ratio": round(new_ratio, 4),
            "high_risk": new_ratio > 0.40,
        }

    raise AppError(ErrorCodes.VALIDATION_ERROR, "Unsupported scenario type", status_code=422)
