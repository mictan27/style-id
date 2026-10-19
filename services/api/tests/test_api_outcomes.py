from conftest import DEV_HEADERS, OTHER_HEADERS, add_grey_tee, check_product
from fastapi.testclient import TestClient


def make_report(client: TestClient) -> str:
    add_grey_tee(client)
    product = check_product(client)
    r = client.post("/v1/fit/reports", json={"product_id": product["id"]}, headers=DEV_HEADERS)
    assert r.status_code == 201, r.text
    report_id: str = r.json()["id"]
    return report_id


def test_tight_return_nudges_chest_up_by_one(client: TestClient) -> None:
    report_id = make_report(client)
    r = client.post(
        "/v1/outcomes",
        json={
            "fit_report_id": report_id,
            "size_bought": "M",
            "kept": False,
            "zone": "chest",
            "direction": "tight",
        },
        headers=DEV_HEADERS,
    )
    assert r.status_code == 201, r.text
    assert r.json()["preferences"] == {"shift_cm": {"chest": 1.0}}
    me = client.get("/v1/me", headers=DEV_HEADERS).json()
    assert me["preferences"]["shift_cm"] == {"chest": 1.0}

    # A loose return in the same zone walks it back.
    r = client.post(
        "/v1/outcomes",
        json={
            "fit_report_id": report_id,
            "size_bought": "L",
            "kept": False,
            "zone": "chest",
            "direction": "loose",
        },
        headers=DEV_HEADERS,
    )
    assert r.json()["preferences"]["shift_cm"] == {"chest": 0.0}


def test_kept_does_not_change_preferences(client: TestClient) -> None:
    report_id = make_report(client)
    r = client.post(
        "/v1/outcomes",
        json={"fit_report_id": report_id, "size_bought": "M", "kept": True},
        headers=DEV_HEADERS,
    )
    assert r.status_code == 201
    assert r.json()["preferences"] == {"shift_cm": {}}


def test_outcome_validation_and_ownership(client: TestClient) -> None:
    report_id = make_report(client)
    half = {"fit_report_id": report_id, "size_bought": "M", "kept": False, "zone": "chest"}
    assert client.post("/v1/outcomes", json=half, headers=DEV_HEADERS).status_code == 422
    other = {"fit_report_id": report_id, "size_bought": "M", "kept": True}
    assert client.post("/v1/outcomes", json=other, headers=OTHER_HEADERS).status_code == 404


def test_preferences_patch_merges(client: TestClient) -> None:
    r = client.patch("/v1/me/preferences", json={"shift_cm": {"chest": 2}}, headers=DEV_HEADERS)
    assert r.status_code == 200 and r.json() == {"shift_cm": {"chest": 2.0}}
    r = client.patch("/v1/me/preferences", json={"shift_cm": {"sleeve": -1}}, headers=DEV_HEADERS)
    assert r.json() == {"shift_cm": {"chest": 2.0, "sleeve": -1.0}}
