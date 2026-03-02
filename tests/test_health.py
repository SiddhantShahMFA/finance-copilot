def test_health_endpoint(client):
    response = client.get("/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["version"] == "v1"
    assert payload["db_connected"] is True
