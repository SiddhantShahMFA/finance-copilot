def test_snapshot_create_and_latest(client, make_token):
    token = make_token(user_id="user-100", role="user")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "month": "2026-03",
        "income_total": 120000,
        "expense_total": 80000,
        "assets_total": 500000,
        "liabilities_total": 100000,
        "emi_total": 25000,
        "liquid_assets": 100000,
        "essential_expense": 45000,
        "credit_limit_total": 200000,
        "credit_outstanding_total": 25000,
    }

    create_resp = client.post("/v1/financial-snapshots", json=payload, headers=headers)
    assert create_resp.status_code == 200
    assert create_resp.json()["month"] == "2026-03-01"

    latest_resp = client.get("/v1/financial-snapshots/latest", headers=headers)
    assert latest_resp.status_code == 200
    assert latest_resp.json()["income_total"] == "120000.00"


def test_snapshot_upsert_updates_existing_month(client, make_token):
    token = make_token(user_id="user-101", role="user")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "month": "2026-03",
        "income_total": 100000,
        "expense_total": 70000,
        "assets_total": 400000,
        "liabilities_total": 150000,
        "emi_total": 20000,
        "liquid_assets": 90000,
        "essential_expense": 35000,
        "credit_limit_total": 100000,
        "credit_outstanding_total": 10000,
    }
    client.post("/v1/financial-snapshots", json=payload, headers=headers)

    payload["income_total"] = 111000
    payload["expense_total"] = 71000
    update_resp = client.post("/v1/financial-snapshots", json=payload, headers=headers)
    assert update_resp.status_code == 200
    assert update_resp.json()["income_total"] == "111000.00"


def test_snapshot_validation_error(client, make_token):
    token = make_token(user_id="user-102", role="user")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "month": "2026-03",
        "income_total": -1,
        "expense_total": 100,
        "assets_total": 100,
        "liabilities_total": 100,
        "emi_total": 100,
        "liquid_assets": 100,
        "essential_expense": 100,
        "credit_limit_total": 100,
        "credit_outstanding_total": 100,
    }

    response = client.post("/v1/financial-snapshots", json=payload, headers=headers)
    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"
