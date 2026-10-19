from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.headers["X-Request-ID"]


def test_request_id_is_echoed(client: TestClient) -> None:
    r = client.get("/v1/health", headers={"X-Request-ID": "abc-123"})
    assert r.headers["X-Request-ID"] == "abc-123"
