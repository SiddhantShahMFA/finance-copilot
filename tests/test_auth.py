from sqlalchemy import select

from app.db.models import AdminAuditLog


def test_auth_required_for_entitlement(client):
    response = client.get("/v1/entitlement/me")
    assert response.status_code == 401
    assert response.json()["error_code"] == "AUTH_INVALID_TOKEN"


def test_valid_user_can_access_entitlement(client, make_token):
    token = make_token(user_id="user-10", role="user")
    response = client.get("/v1/entitlement/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["user_id"] == "user-10"
    assert response.json()["plan"] == "free"


def test_non_admin_cannot_patch_subscription(client, make_token):
    user_token = make_token(user_id="user-1", role="user")
    response = client.patch(
        "/v1/admin/subscriptions/user-2",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"plan": "premium", "status": "active", "expiry_date": None},
    )
    assert response.status_code == 403
    assert response.json()["error_code"] == "AUTH_FORBIDDEN"


def test_admin_can_patch_subscription_and_writes_audit(client, make_token, db_session):
    admin_token = make_token(user_id="admin-1", role="admin")
    response = client.patch(
        "/v1/admin/subscriptions/user-2",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"plan": "premium", "status": "active", "expiry_date": None},
    )
    assert response.status_code == 200
    assert response.json()["plan"] == "premium"

    logs = db_session.execute(select(AdminAuditLog)).scalars().all()
    assert len(logs) == 1
    assert logs[0].actor_user_id == "admin-1"
    assert logs[0].target_user_id == "user-2"
