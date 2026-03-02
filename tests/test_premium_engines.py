def _seed_snapshot(client, token, **overrides):
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "month": "2026-03",
        "income_total": 150000,
        "expense_total": 90000,
        "assets_total": 600000,
        "liabilities_total": 200000,
        "emi_total": 45000,
        "liquid_assets": 250000,
        "essential_expense": 50000,
        "credit_limit_total": 300000,
        "credit_outstanding_total": 90000,
    }
    payload.update(overrides)
    response = client.post("/v1/financial-snapshots", json=payload, headers=headers)
    assert response.status_code == 200


def test_health_score_requires_auth(client):
    response = client.get("/v1/health-score")
    assert response.status_code == 401
    assert response.json()["error_code"] == "AUTH_INVALID_TOKEN"


def test_health_score_and_debt_insights(client, make_token):
    token = make_token(user_id="u-premium", role="user")
    headers = {"Authorization": f"Bearer {token}"}
    _seed_snapshot(client, token)

    score_resp = client.get("/v1/health-score", headers=headers)
    assert score_resp.status_code == 200
    score_json = score_resp.json()
    assert 0 <= score_json["total_score"] <= 100
    assert len(score_json["components"]) == 5

    debt_resp = client.get("/v1/debt/insights", headers=headers)
    assert debt_resp.status_code == 200
    debt_json = debt_resp.json()
    assert debt_json["emi_income_ratio"] == 0.3
    assert debt_json["stress_band"] in {"low", "moderate", "high"}


def test_cashflow_goal_and_simulation(client, make_token):
    token = make_token(user_id="u-goal", role="user")
    headers = {"Authorization": f"Bearer {token}"}
    _seed_snapshot(client, token, expense_total=100000)

    cash_resp = client.get("/v1/cashflow/insights", headers=headers)
    assert cash_resp.status_code == 200
    assert cash_resp.json()["monthly_surplus"] == 50000.0

    goal_resp = client.get(
        "/v1/goals/feasibility",
        headers=headers,
        params={
            "target_amount": 1200000,
            "current_savings": 300000,
            "remaining_months": 18,
            "monthly_contribution": 60000,
        },
    )
    assert goal_resp.status_code == 200
    goal_json = goal_resp.json()
    assert goal_json["required_monthly_saving"] == 50000.0
    assert goal_json["confidence_band"] in {"high", "moderate", "at_risk"}

    sim_resp = client.post(
        "/v1/simulations/run",
        headers=headers,
        json={
            "scenario": "affordability_check",
            "params": {
                "purchase_amount": 600000,
                "upfront_ratio": 0.2,
                "tenure_months": 24,
            },
        },
    )
    assert sim_resp.status_code == 200
    sim_json = sim_resp.json()
    assert sim_json["scenario"] == "affordability_check"
    assert sim_json["output"]["decision"] in {"yes", "conditional_yes", "no"}


def test_simulation_validation_error(client, make_token):
    token = make_token(user_id="u-sim", role="user")
    headers = {"Authorization": f"Bearer {token}"}
    _seed_snapshot(client, token)

    response = client.post(
        "/v1/simulations/run",
        headers=headers,
        json={"scenario": "sip_increase", "params": {"increase_amount": 0}},
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"
