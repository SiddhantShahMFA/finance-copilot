def _seed_snapshot(client, token):
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "month": "2026-03",
        "income_total": 180000,
        "expense_total": 105000,
        "assets_total": 900000,
        "liabilities_total": 250000,
        "emi_total": 45000,
        "liquid_assets": 300000,
        "essential_expense": 60000,
        "credit_limit_total": 400000,
        "credit_outstanding_total": 120000,
    }
    response = client.post("/v1/financial-snapshots", json=payload, headers=headers)
    assert response.status_code == 200


def test_copilot_rejects_unsupported_prompt(client, make_token):
    token = make_token(user_id="copilot-user", role="user")
    _seed_snapshot(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/v1/copilot/query",
        headers=headers,
        json={"question": "Suggest best mutual funds for me", "params": {}},
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"


def test_copilot_allows_free_intent_for_free_user(client, make_token):
    token = make_token(user_id="free-user", role="user")
    _seed_snapshot(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/v1/copilot/query",
        headers=headers,
        json={"question": "How much do I spend monthly?", "params": {}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent_id"] == "monthly_spend_summary"
    assert data["tier"] == "free"
    assert data["explanation_source"] == "fallback"


def test_copilot_blocks_premium_intent_for_free_user(client, make_token):
    token = make_token(user_id="free-blocked", role="user")
    _seed_snapshot(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/v1/copilot/query",
        headers=headers,
        json={"question": "Can I increase my SIP by 10000?", "params": {"increase_amount": 10000}},
    )
    assert response.status_code == 403
    assert response.json()["error_code"] == "ENTITLEMENT_REQUIRED"


def test_copilot_allows_premium_intent_for_premium_user(client, make_token):
    admin_token = make_token(user_id="admin-2", role="admin")
    user_token = make_token(user_id="premium-user", role="user")
    _seed_snapshot(client, user_token)

    # Upgrade user to premium manually.
    patch_response = client.patch(
        "/v1/admin/subscriptions/premium-user",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"plan": "premium", "status": "active", "expiry_date": None},
    )
    assert patch_response.status_code == 200

    response = client.post(
        "/v1/copilot/query",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"question": "Can I increase my SIP by 10000?", "params": {"increase_amount": 10000}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent_id"] == "sip_increase"
    assert data["tier"] == "premium"
    assert "safe_increment" in data["computed_metrics"]
    assert data["explanation_source"] == "fallback"
