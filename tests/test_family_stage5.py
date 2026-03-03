def _seed_snapshot(client, token, income=140000, expense=90000, assets=700000, liabilities=200000):
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "month": "2026-03",
        "income_total": income,
        "expense_total": expense,
        "assets_total": assets,
        "liabilities_total": liabilities,
        "emi_total": 30000,
        "liquid_assets": 180000,
        "essential_expense": 50000,
        "credit_limit_total": 300000,
        "credit_outstanding_total": 80000,
    }
    response = client.post("/v1/financial-snapshots", json=payload, headers=headers)
    assert response.status_code == 200


def _upgrade_to_premium(client, admin_token, user_id):
    response = client.patch(
        f"/v1/admin/subscriptions/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"plan": "premium", "status": "active", "expiry_date": None},
    )
    assert response.status_code == 200


def test_family_endpoints_require_premium(client, make_token):
    user_token = make_token(user_id="family-free", role="user")
    _seed_snapshot(client, user_token)

    response = client.post(
        "/v1/family/households",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"name": "My Family"},
    )
    assert response.status_code == 403
    assert response.json()["error_code"] == "ENTITLEMENT_REQUIRED"


def test_family_household_flow(client, make_token):
    admin_token = make_token(user_id="admin-family", role="admin")
    owner_token = make_token(user_id="family-owner", role="user")
    member_token = make_token(user_id="family-member", role="user")

    _seed_snapshot(client, owner_token, income=160000, expense=100000, assets=900000, liabilities=250000)
    _seed_snapshot(client, member_token, income=110000, expense=70000, assets=500000, liabilities=150000)

    _upgrade_to_premium(client, admin_token, "family-owner")
    _upgrade_to_premium(client, admin_token, "family-member")

    create_household = client.post(
        "/v1/family/households",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"name": "Shah Household"},
    )
    assert create_household.status_code == 200
    household_id = create_household.json()["id"]

    add_member = client.post(
        f"/v1/family/households/{household_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"user_id": "family-member", "role": "member"},
    )
    assert add_member.status_code == 200
    assert add_member.json()["member_count"] == 2

    add_goal = client.post(
        f"/v1/family/households/{household_id}/goals",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "name": "Family Vacation",
            "target_amount": 300000,
            "current_savings": 80000,
            "remaining_months": 10,
            "monthly_contribution": 25000,
        },
    )
    assert add_goal.status_code == 200

    overview = client.get(
        "/v1/family/overview",
        headers={"Authorization": f"Bearer {member_token}"},
        params={"household_id": household_id},
    )
    assert overview.status_code == 200
    data = overview.json()
    assert data["household_id"] == household_id
    assert data["shared_net_worth"] == 1000000.0
    assert data["combined_goal_target"] == 300000.0
    assert data["combined_goal_current_savings"] == 80000.0
    assert len(data["contribution_breakdown"]) == 2
    assert data["family_health_score"] > 0
