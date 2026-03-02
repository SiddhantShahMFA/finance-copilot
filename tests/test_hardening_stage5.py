def _seed_snapshot(client, token):
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "month": "2026-03",
        "income_total": 120000,
        "expense_total": 80000,
        "assets_total": 600000,
        "liabilities_total": 180000,
        "emi_total": 25000,
        "liquid_assets": 120000,
        "essential_expense": 45000,
        "credit_limit_total": 200000,
        "credit_outstanding_total": 50000,
    }
    response = client.post("/v1/financial-snapshots", json=payload, headers=headers)
    assert response.status_code == 200


def test_observability_endpoint_tracks_requests(client, make_token):
    admin_token = make_token(user_id="admin-obsv", role="admin")
    user_token = make_token(user_id="obsv-user", role="user")

    _seed_snapshot(client, user_token)

    client.get("/v1/health")
    client.post(
        "/v1/copilot/query",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"question": "How much do I spend monthly?", "params": {}},
    )

    response = client.get("/v1/admin/observability", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["total_requests"] >= 2
    assert isinstance(data["endpoints"], list)
    assert any(item["endpoint"].startswith("POST /v1/copilot/query") for item in data["endpoints"])


def test_rate_limit_blocks_excess_copilot_requests(client, make_token):
    user_token = make_token(user_id="ratelimit-user", role="user")
    _seed_snapshot(client, user_token)

    headers = {"Authorization": f"Bearer {user_token}"}
    limited_response = None
    for _ in range(6):  # RATE_LIMIT_REQUESTS=5 in test env
        response = client.post(
            "/v1/copilot/query",
            headers=headers,
            json={"question": "How much do I spend monthly?", "params": {}},
        )
        if response.status_code == 429:
            limited_response = response
            break

    assert limited_response is not None
    assert limited_response.json()["error_code"] == "RATE_LIMIT_EXCEEDED"
