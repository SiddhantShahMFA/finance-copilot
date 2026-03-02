from datetime import datetime

from sqlalchemy import select

from app.db.models import AccountLink, AdminAuditLog, UserEntitlement


def _seed_snapshot(client, token, income=200000, expense=120000, assets=800000):
    headers = {"Authorization": f"Bearer {token}"}
    month = datetime.now().strftime("%Y-%m")
    payload = {
        "month": month,
        "income_total": income,
        "expense_total": expense,
        "assets_total": assets,
        "liabilities_total": 300000,
        "emi_total": 60000,
        "liquid_assets": 250000,
        "essential_expense": 70000,
        "credit_limit_total": 500000,
        "credit_outstanding_total": 150000,
    }
    response = client.post("/v1/financial-snapshots", json=payload, headers=headers)
    assert response.status_code == 200


def test_admin_overview_and_subscriptions(client, make_token):
    admin_token = make_token(user_id="admin", role="admin")
    user1_token = make_token(user_id="u1", role="user")
    user2_token = make_token(user_id="u2", role="user")

    _seed_snapshot(client, user1_token)
    _seed_snapshot(client, user2_token)

    patch_response = client.patch(
        "/v1/admin/subscriptions/u1",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"plan": "premium", "status": "active", "expiry_date": None},
    )
    assert patch_response.status_code == 200

    overview = client.get("/v1/admin/overview", headers={"Authorization": f"Bearer {admin_token}"})
    assert overview.status_code == 200
    overview_json = overview.json()
    assert overview_json["total_registered_users"] == 2
    assert overview_json["monthly_active_users"] == 2
    assert overview_json["total_premium_users"] == 1
    assert overview_json["conversion_rate"] == 50.0

    subscriptions = client.get("/v1/admin/subscriptions", headers={"Authorization": f"Bearer {admin_token}"})
    assert subscriptions.status_code == 200
    items = {item["user_id"]: item for item in subscriptions.json()["items"]}
    assert items["u1"]["plan"] == "premium"
    assert items["u2"]["plan"] == "free"


def test_admin_ai_usage_and_data_health(client, make_token, db_session):
    admin_token = make_token(user_id="admin", role="admin")
    user_token = make_token(user_id="usage-user", role="user")

    _seed_snapshot(client, user_token, assets=900000)

    db_session.add_all(
        [
            AccountLink(
                user_id="usage-user",
                account_type="bank",
                provider="aa",
                external_account_id="bank-1",
                status="linked",
            ),
            AccountLink(
                user_id="usage-user",
                account_type="mf",
                provider="aa",
                external_account_id="mf-1",
                status="linked",
            ),
            AccountLink(
                user_id="usage-user",
                account_type="stock",
                provider="aa",
                external_account_id="stock-1",
                status="linked",
            ),
        ]
    )
    db_session.commit()

    headers = {"Authorization": f"Bearer {user_token}"}
    ok = client.post(
        "/v1/copilot/query",
        headers=headers,
        json={"question": "How much do I spend monthly?", "params": {}},
    )
    assert ok.status_code == 200

    failed = client.post(
        "/v1/copilot/query",
        headers=headers,
        json={"question": "Give me stock tips", "params": {}},
    )
    assert failed.status_code == 422

    ai_usage = client.get("/v1/admin/ai-usage", headers={"Authorization": f"Bearer {admin_token}"})
    assert ai_usage.status_code == 200
    ai_json = ai_usage.json()
    assert ai_json["total_prompts_used"] == 2
    assert ai_json["failed_prompts"] == 1
    assert "How much do I spend monthly?" in ai_json["top_asked_questions"]

    health = client.get("/v1/admin/data-health", headers={"Authorization": f"Bearer {admin_token}"})
    assert health.status_code == 200
    health_json = health.json()
    assert health_json["linked_bank_accounts_count"] == 1
    assert health_json["linked_mf_count"] == 1
    assert health_json["linked_stock_accounts_count"] == 1
    assert health_json["avg_assets_per_user"] == 900000.0


def test_admin_user_controls_and_audit_logs(client, make_token, db_session):
    admin_token = make_token(user_id="admin", role="admin")

    suspend = client.post(
        "/v1/admin/users/target-user/suspend",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "manual moderation"},
    )
    assert suspend.status_code == 200
    assert suspend.json()["action"] == "SUSPEND_USER"

    reset = client.post(
        "/v1/admin/users/target-user/reset-password",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reset.status_code == 200
    assert reset.json()["action"] == "RESET_PASSWORD_REQUESTED"

    entitlement = db_session.get(UserEntitlement, "target-user")
    assert entitlement is not None
    assert entitlement.status.value == "inactive"

    actions = db_session.execute(select(AdminAuditLog.action)).scalars().all()
    assert "SUSPEND_USER" in actions
    assert "RESET_PASSWORD_REQUESTED" in actions
