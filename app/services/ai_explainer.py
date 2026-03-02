import re

import httpx

from app.core.config import get_settings


PROHIBITED_ADVICE_PATTERNS = (
    r"\bbuy\b",
    r"\bsell\b",
    r"\brecommend(?:ed|ation)?\b",
    r"\binvest in\b",
    r"\bmutual fund\b",
    r"\bstock tip\b",
)

SAFETY_NOTE = "This response is analysis-only, not product advice or buy/sell guidance."


def _fallback_explanation(intent_id: str, computed_metrics: dict, tradeoffs: list[str], risk_flags: list[str]) -> str:
    metrics = ", ".join([f"{k}={v}" for k, v in computed_metrics.items()])
    risks = ", ".join(risk_flags) if risk_flags else "no critical risk flags"
    tradeoff_text = "; ".join(tradeoffs) if tradeoffs else "No major trade-offs detected"
    return (
        f"Intent: {intent_id}. Key metrics: {metrics}. Risks: {risks}. "
        f"Trade-offs: {tradeoff_text}. {SAFETY_NOTE}"
    )


def _violates_policy(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in PROHIBITED_ADVICE_PATTERNS)


def generate_explanation(intent_id: str, computed_metrics: dict, risk_flags: list[str], tradeoffs: list[str]) -> tuple[str, str]:
    settings = get_settings()

    if not settings.openai_api_key:
        return _fallback_explanation(intent_id, computed_metrics, tradeoffs, risk_flags), "fallback"

    system_prompt = (
        "You are a financial analysis narrator. You must only explain structured metrics supplied by the system. "
        "Do not provide product recommendations, do not advise buy/sell actions, and always mention trade-offs and risk."
    )
    user_prompt = (
        f"intent_id={intent_id}\n"
        f"computed_metrics={computed_metrics}\n"
        f"risk_flags={risk_flags}\n"
        f"tradeoffs={tradeoffs}\n"
        "Write a concise user-facing explanation in plain English with quantified impact when available."
    )

    try:
        response = httpx.post(
            f"{settings.openai_base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openai_model,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=settings.openai_timeout_seconds,
        )
        response.raise_for_status()
        content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        if not content:
            return _fallback_explanation(intent_id, computed_metrics, tradeoffs, risk_flags), "fallback"
        if _violates_policy(content):
            return _fallback_explanation(intent_id, computed_metrics, tradeoffs, risk_flags), "fallback"
        return f"{content} {SAFETY_NOTE}", "openai"
    except Exception:
        return _fallback_explanation(intent_id, computed_metrics, tradeoffs, risk_flags), "fallback"
