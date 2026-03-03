def test_e2e_regression_family_and_admin_flow(client, make_token):
    admin_token = make_token(user_id="admin-e2e", role="admin")
    owner_token = make_token(user_id="owner-e2e", role="user")
    partner_token = make_token(user_id="partner-e2e", role="user")

    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    partner_headers = {"Authorization": f"Bearer {partner_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    owner_snapshot = {
        "month": "2026-03",
        "income_total": 180000,
        "expense_total": 110000,
        "assets_total": 1200000,
        "liabilities_total": 350000,
        "emi_total": 55000,
        "liquid_assets": 300000,
        "essential_expense": 65000,
        "credit_limit_total": 450000,
        "credit_outstanding_total": 125000,
    }
    partner_snapshot = {
        "month": "2026-03",
        "income_total": 130000,
        "expense_total": 85000,
        "assets_total": 650000,
        "liabilities_total": 150000,
        "emi_total": 25000,
        "liquid_assets": 200000,
        "essential_expense": 50000,
        "credit_limit_total": 250000,
        "credit_outstanding_total": 50000,
    }

    assert client.post("/v1/financial-snapshots", headers=owner_headers, json=owner_snapshot).status_code == 200
    assert client.post("/v1/financial-snapshots", headers=partner_headers, json=partner_snapshot).status_code == 200

    assert (
        client.patch(
            "/v1/admin/subscriptions/owner-e2e",
            headers=admin_headers,
            json={"plan": "premium", "status": "active", "expiry_date": None},
        ).status_code
        == 200
    )
    assert (
        client.patch(
            "/v1/admin/subscriptions/partner-e2e",
            headers=admin_headers,
            json={"plan": "premium", "status": "active", "expiry_date": None},
        ).status_code
        == 200
    )

    create_household = client.post(
        "/v1/family/households", headers=owner_headers, json={"name": "E2E Family"}
    )
    assert create_household.status_code == 200
    household_id = create_household.json()["id"]

    assert (
        client.post(
            f"/v1/family/households/{household_id}/members",
            headers=owner_headers,
            json={"user_id": "partner-e2e", "role": "member"},
        ).status_code
        == 200
    )

    assert (
        client.post(
            f"/v1/family/households/{household_id}/goals",
            headers=owner_headers,
            json={
                "name": "House Downpayment",
                "target_amount": 2000000,
                "current_savings": 400000,
                "remaining_months": 24,
                "monthly_contribution": 75000,
            },
        ).status_code
        == 200
    )

    family_overview = client.get(
        "/v1/family/overview",
        headers=partner_headers,
        params={"household_id": household_id},
    )
    assert family_overview.status_code == 200
    overview_json = family_overview.json()
    assert overview_json["shared_net_worth"] == 1350000.0
    assert overview_json["combined_goal_target"] == 2000000.0

    copilot_resp = client.post(
        "/v1/copilot/query",
        headers=owner_headers,
        json={"question": "Can I increase my SIP by 10000?", "params": {"increase_amount": 10000}},
    )
    assert copilot_resp.status_code == 200
    assert copilot_resp.json()["tier"] == "premium"

    admin_usage = client.get("/v1/admin/ai-usage", headers=admin_headers)
    assert admin_usage.status_code == 200
    assert admin_usage.json()["total_prompts_used"] >= 1

    observability = client.get("/v1/admin/observability", headers=admin_headers)
    assert observability.status_code == 200
    assert observability.json()["total_requests"] > 0
