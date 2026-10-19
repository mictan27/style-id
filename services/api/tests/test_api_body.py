from conftest import AVG_BODY, DEV_HEADERS, verify_age
from fastapi.testclient import TestClient


def test_body_record_requires_age_verification(client: TestClient) -> None:
    r = client.post("/v1/body/records", json=AVG_BODY, headers=DEV_HEADERS)
    assert r.status_code == 403
    assert "18" in r.json()["detail"]
    verify_age(client)
    r = client.post("/v1/body/records", json=AVG_BODY, headers=DEV_HEADERS)
    assert r.status_code == 201, r.text
    assert r.json()["is_current"] is True
    assert r.json()["confirmed_at"] is None


def test_current_and_confirm_with_override(client: TestClient) -> None:
    assert client.get("/v1/body/records/current", headers=DEV_HEADERS).status_code == 404
    verify_age(client)
    first = client.post("/v1/body/records", json=AVG_BODY, headers=DEV_HEADERS).json()
    second = client.post(
        "/v1/body/records", json={**AVG_BODY, "source": "photo"}, headers=DEV_HEADERS
    ).json()

    current = client.get("/v1/body/records/current", headers=DEV_HEADERS).json()
    assert current["id"] == second["id"] and current["source"] == "photo"
    assert (
        client.get(f"/v1/body/records/{first['id']}", headers=DEV_HEADERS).json()["is_current"]
        is False
    )

    r = client.post(
        f"/v1/body/records/{second['id']}/confirm",
        json={"overrides": {"chest": 98.5, "waist": 86}},
        headers=DEV_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["confirmed_at"] is not None
    assert body["measurements"]["chest"] == {
        "value_cm": 98.5,
        "source": "manual",
        "confidence": "high",
    }
    assert body["measurements"]["waist"]["source"] == "manual"
    # Untouched fields keep their scanner provenance.
    assert body["measurements"]["hip"] == AVG_BODY["measurements"]["hip"]
    assert body["landmarks"] == AVG_BODY["landmarks"]
