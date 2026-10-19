from conftest import DEV_HEADERS, GREY_TEE, OTHER_HEADERS, add_grey_tee
from fastapi.testclient import TestClient

from styleid_schema import GarmentModel


def test_closet_crud_round_trip(client: TestClient) -> None:
    created = add_grey_tee(client)
    assert created["name"] == "grey tee" and created["is_reference"] is True
    # The stored garment is a valid GarmentModel with the same numbers.
    model = GarmentModel.model_validate(created)
    assert model.measurements[model.measurements.__iter__().__next__()].value_cm == 50
    assert model.to_engine().value(next(iter(model.measurements))) == 50

    listed = client.get("/v1/closet/garments", headers=DEV_HEADERS).json()
    assert [g["id"] for g in listed] == [created["id"]]

    got = client.get(f"/v1/closet/garments/{created['id']}", headers=DEV_HEADERS).json()
    assert got == created

    updated_payload = {**GREY_TEE, "name": "grey tee (washed)", "is_reference": False}
    updated_payload["measurements"] = {
        **GREY_TEE["measurements"],
        "chest_width": {"value_cm": 49.5, "source": "flatlay", "confidence": "high"},
    }
    r = client.put(
        f"/v1/closet/garments/{created['id']}", json=updated_payload, headers=DEV_HEADERS
    )
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "grey tee (washed)"
    assert r.json()["is_reference"] is False
    assert r.json()["measurements"]["chest_width"]["value_cm"] == 49.5

    # Another user cannot see or delete it.
    assert (
        client.get(f"/v1/closet/garments/{created['id']}", headers=OTHER_HEADERS).status_code == 404
    )
    assert (
        client.delete(f"/v1/closet/garments/{created['id']}", headers=OTHER_HEADERS).status_code
        == 404
    )

    assert (
        client.delete(f"/v1/closet/garments/{created['id']}", headers=DEV_HEADERS).status_code
        == 204
    )
    assert client.get("/v1/closet/garments", headers=DEV_HEADERS).json() == []


def test_closet_rejects_bad_measurement(client: TestClient) -> None:
    bad = {**GREY_TEE, "measurements": {"chest_width": {"value_cm": -1, "source": "flatlay"}}}
    assert client.post("/v1/closet/garments", json=bad, headers=DEV_HEADERS).status_code == 422


def test_landmark_corrections(client: TestClient) -> None:
    garment = add_grey_tee(client)
    payload = {
        "image_blob_key": "closet/alice/grey-tee.jpg",
        "proposed": {"left_pit": {"x": 100, "y": 220}, "right_pit": {"x": 620, "y": 224}},
        "corrected": {"left_pit": {"x": 104, "y": 221}, "right_pit": {"x": 618, "y": 224}},
        "scale_cm_per_px": 0.097,
    }
    r = client.post(
        f"/v1/closet/garments/{garment['id']}/landmark-corrections",
        json=payload,
        headers=DEV_HEADERS,
    )
    assert r.status_code == 201, r.text
    assert r.json()["corrected"]["left_pit"] == {"x": 104, "y": 221}
    listed = client.get(
        f"/v1/closet/garments/{garment['id']}/landmark-corrections", headers=DEV_HEADERS
    ).json()
    assert len(listed) == 1 and listed[0]["garment_id"] == garment["id"]
