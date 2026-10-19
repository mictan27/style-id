import json
import subprocess
import sys

from fastapi import FastAPI

from styleid_api.openapi import camel_case, openapi_document, operation_ids

EXPECTED = {
    "getHealth",
    "signInWithApple",
    "getMe",
    "updateMe",
    "updatePreferences",
    "listClosetGarments",
    "createClosetGarment",
    "getClosetGarment",
    "updateClosetGarment",
    "deleteClosetGarment",
    "createLandmarkCorrection",
    "listLandmarkCorrections",
    "createBodyRecord",
    "getCurrentBodyRecord",
    "getBodyRecord",
    "confirmBodyRecord",
    "checkProduct",
    "getProduct",
    "createFitReport",
    "listFitReports",
    "getFitReport",
    "createOutcome",
}


def test_camel_case() -> None:
    assert camel_case("list_closet_garments") == "listClosetGarments"
    assert camel_case("health") == "health"


def test_operation_ids_are_camel_case_and_unique(app: FastAPI) -> None:
    ids = operation_ids(app)
    assert set(ids) == EXPECTED
    doc = openapi_document(app)
    found = {op["operationId"] for path in doc["paths"].values() for op in path.values()}
    assert found == EXPECTED
    tags = {t for path in doc["paths"].values() for op in path.values() for t in op["tags"]}
    assert tags == {"health", "auth", "me", "closet", "body", "products", "fit", "outcomes"}
    # The shared vocabulary is reused, not redefined.
    assert {"FitReportModel", "PreferencesModel", "MeasurementModel", "Zone", "GarmentKind"} <= set(
        doc["components"]["schemas"]
    )


def test_module_prints_valid_json() -> None:
    out = subprocess.run(
        [sys.executable, "-m", "styleid_api.openapi"],
        check=True,
        capture_output=True,
        text=True,
        env={"STYLEID_DATABASE_URL": "sqlite+pysqlite://", "PATH": ""},
    ).stdout
    doc = json.loads(out)
    assert doc["info"]["title"] == "style.id API"
    assert "/v1/fit/reports" in doc["paths"]
