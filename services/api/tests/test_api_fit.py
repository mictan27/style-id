from pathlib import Path
from typing import Any

from conftest import (
    AVG_BODY,
    DEV_HEADERS,
    OTHER_HEADERS,
    add_grey_tee,
    build_app,
    check_product,
    make_settings,
    verify_age,
)
from fastapi.testclient import TestClient

from styleid_fit import Basis, Label, Zone
from styleid_schema import FitReportModel


def test_fit_report_end_to_end_picks_m(client: TestClient) -> None:
    tee = add_grey_tee(client)
    product = check_product(client)
    r = client.post("/v1/fit/reports", json={"product_id": product["id"]}, headers=DEV_HEADERS)
    assert r.status_code == 201, r.text
    out = r.json()
    report = FitReportModel.model_validate(out["report"])
    assert report.pick is not None and report.pick.size_label == "M"
    assert report.reference_size_label == "M"
    assert {s.size_label for s in report.sizes} == {"S", "M", "L"}
    chest = next(z for z in report.pick.zones if z.zone is Zone.CHEST)
    assert chest.basis is Basis.REFERENCE and chest.delta_vs_ref_cm == 0
    assert chest.label is Label.REGULAR
    assert out["reference_garment_id"] == tee["id"]
    assert out["body_record_id"] is None
    assert out["product"]["id"] == product["id"]

    got = client.get(f"/v1/fit/reports/{out['id']}", headers=DEV_HEADERS)
    assert got.status_code == 200 and got.json()["report"] == out["report"]
    assert client.get(f"/v1/fit/reports/{out['id']}", headers=OTHER_HEADERS).status_code == 404

    listed = client.get("/v1/fit/reports", headers=DEV_HEADERS).json()
    assert [x["id"] for x in listed] == [out["id"]]


def test_fit_report_uses_current_body_and_explicit_references(client: TestClient) -> None:
    verify_age(client)
    body = client.post("/v1/body/records", json=AVG_BODY, headers=DEV_HEADERS).json()
    tee = add_grey_tee(client)
    product = check_product(client)
    r = client.post(
        "/v1/fit/reports",
        json={"product_id": product["id"], "reference_garment_ids": [tee["id"]]},
        headers=DEV_HEADERS,
    )
    assert r.status_code == 201, r.text
    assert r.json()["body_record_id"] == body["id"]
    report = FitReportModel.model_validate(r.json()["report"])
    assert report.pick is not None and report.pick.size_label == "M"
    chest = next(z for z in report.pick.zones if z.zone is Zone.CHEST)
    assert chest.ease_cm == 4  # 2 * 50 - 96

    bad = client.post(
        "/v1/fit/reports",
        json={"product_id": product["id"], "reference_garment_ids": ["nope"]},
        headers=DEV_HEADERS,
    )
    assert bad.status_code == 404


def test_fit_report_409_when_chart_pending(tmp_path: Path, jwks_store: dict[str, Any]) -> None:
    class NeverRuns:
        def run(self, size_chart_id: str) -> None:
            return None

    app = build_app(make_settings(tmp_path), jwks_store, runner=NeverRuns())
    with TestClient(app) as client:
        product = check_product(client)
        assert product["chart"]["status"] == "pending"
        r = client.post("/v1/fit/reports", json={"product_id": product["id"]}, headers=DEV_HEADERS)
        assert r.status_code == 409
        assert "still running" in r.json()["detail"]


def test_fit_report_404_for_unknown_product(client: TestClient) -> None:
    r = client.post("/v1/fit/reports", json={"product_id": "missing"}, headers=DEV_HEADERS)
    assert r.status_code == 404
