from dataclasses import dataclass

from app.core.errors import AppError, ErrorCodes


@dataclass(frozen=True)
class IntentDefinition:
    intent_id: str
    tier: str
    patterns: tuple[str, ...]


INTENT_DEFINITIONS: tuple[IntentDefinition, ...] = (
    IntentDefinition("overspending_summary", "free", ("overspend", "overspending", "spend too much")),
    IntentDefinition("savings_rate_summary", "free", ("savings rate", "save monthly", "current savings rate")),
    IntentDefinition("monthly_spend_summary", "free", ("monthly spend", "how much do i spend", "spend monthly")),
    IntentDefinition("affordability_check", "premium", ("can i afford", "afford", "buy this")),
    IntentDefinition("lifestyle_inflation_detection", "premium", ("lifestyle", "getting expensive", "inflation")),
    IntentDefinition("sip_increase", "premium", ("increase my sip", "sip by", "increase sip")),
    IntentDefinition("goal_feasibility_check", "premium", ("goal realistic", "goal feasibility", "on track for my goal")),
    IntentDefinition("goal_conflict_detection", "premium", ("goals clashing", "goal conflict", "goals overlap")),
    IntentDefinition("delay_impact_analysis", "premium", ("delay this goal", "delay impact", "if i delay")),
    IntentDefinition("debt_stress_analysis", "premium", ("debt level healthy", "debt stress", "debt level")),
    IntentDefinition("emi_overload_warning", "premium", ("emi increase risk", "taking this emi", "emi risk")),
    IntentDefinition("credit_card_behavior", "premium", ("credit cards correctly", "credit utilization", "credit card")),
    IntentDefinition("subscription_leak_detection", "premium", ("wasting money", "unused subscriptions", "subscription leak")),
    IntentDefinition("safe_spend_limit", "premium", ("spend guilt-free", "safe spend", "how much can i spend")),
    IntentDefinition("income_shock_simulation", "premium", ("income drops", "income drop", "income shock")),
    IntentDefinition("family_readiness_check", "premium", ("ready to have a child", "family readiness", "financially ready")),
    IntentDefinition("long_term_trajectory", "premium", ("net worth in 10 years", "retire", "long-term trajectory")),
    IntentDefinition("annual_review", "premium", ("yearly financial review", "annual financial health review", "yearly review")),
)


def resolve_intent(question: str) -> IntentDefinition:
    query = question.strip().lower()
    for definition in INTENT_DEFINITIONS:
        for pattern in definition.patterns:
            if pattern in query:
                return definition

    raise AppError(
        ErrorCodes.VALIDATION_ERROR,
        "Unsupported prompt. Use one of the approved Finance Copilot intents.",
        status_code=422,
    )
