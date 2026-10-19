"""Drive the real API (SQLite, dev auth, fake chart extractor) through a realistic flow and
save every response the mobile app reads as ``apps/mobile/src/test/fixtures/api.json``.

The fit report numbers come from the real ``styleid_fit`` engine, and the shapes come from
the real routes, so the app's screen tests and web screenshots run against data the server
can actually produce. UUIDs and timestamps are replaced with stable values so the file
only changes when the API or the engine changes.

    uv run python services/api/scripts/export_mobile_fixtures.py
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from styleid_api.config import Settings
from styleid_api.db.session import create_all, make_engine
from styleid_api.main import create_app
from styleid_schema import (
    ChartClassification,
    ChartStatus,
    Confidence,
    Cut,
    GarmentKind,
    GarmentModel,
    MeasurementModel,
    NormalisedChart,
    Source,
    StretchClass,
)

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "apps/mobile/src/test/fixtures/api.json"
HEADERS = {"X-Dev-User": "demo"}
PRODUCT_URL = "https://shop.example.com/products/heavyweight-tee?variant=123"

CHART: dict[str, dict[str, float]] = {
    "S": {
        "chest_width": 50,
        "shoulder_width": 44,
        "hem_width": 49,
        "length": 69,
        "sleeve_length": 20,
        "bicep_width": 18,
    },
    "M": {
        "chest_width": 53,
        "shoulder_width": 46,
        "hem_width": 52,
        "length": 71,
        "sleeve_length": 21,
        "bicep_width": 19,
    },
    "L": {
        "chest_width": 56,
        "shoulder_width": 48,
        "hem_width": 55,
        "length": 73,
        "sleeve_length": 22,
        "bicep_width": 20,
    },
    "XL": {
        "chest_width": 59,
        "shoulder_width": 50,
        "hem_width": 58,
        "length": 75,
        "sleeve_length": 23,
        "bicep_width": 21,
    },
}


def m(value: float, source: str, confidence: str = "high") -> dict[str, Any]:
    return {"value_cm": value, "source": source, "confidence": confidence}


def fake_extract(url: str, garment_kind: GarmentKind) -> NormalisedChart:
    sizes = [
        GarmentModel(
            kind=garment_kind,
            cut=Cut.SET_IN,
            stretch=StretchClass.COTTON_JERSEY,
            size_label=label,
            measurements={
                f: MeasurementModel(value_cm=v, source=Source.CHART, confidence=Confidence.HIGH)
                for f, v in fields.items()
            },
        )
        for label, fields in CHART.items()
    ]
    return NormalisedChart(
        status=ChartStatus.OK,
        classification=ChartClassification(chart_kind="garment", measure_basis="flat", unit="cm"),
        stretch=StretchClass.COTTON_JERSEY,
        fabric_composition="100% cotton, 240 gsm",
        sizes=sizes,
        warnings=[],
        model_id="fixture-extractor",
    )


def ok(r: Any, status: int = 200) -> Any:
    if r.status_code != status:
        sys.exit(f"{r.request.method} {r.request.url} -> {r.status_code}: {r.text}")
    return r.json()


def main() -> None:
    routes: list[dict[str, Any]] = []

    def record(method: str, path: str, status: int, body: Any) -> Any:
        routes.append({"method": method, "path": path, "status": status, "body": body})
        return body

    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(
            _env_file=None,
            database_url=f"sqlite+pysqlite:///{Path(tmp) / 'fixtures.db'}",
            dev_auth_enabled=True,
            jwt_secret="fixture-secret",
        )
        engine = make_engine(settings.database_url)
        create_all(engine)
        app = create_app(settings, engine=engine, extract_fn=fake_extract)
        with TestClient(app) as c:
            ok(c.patch("/v1/me", json={"dob_verified_18": True}, headers=HEADERS))

            tee = ok(
                c.post(
                    "/v1/closet/garments",
                    headers=HEADERS,
                    json={
                        "kind": "tee",
                        "cut": "set_in",
                        "stretch": "cotton_jersey",
                        "size_label": "M",
                        "fit_tag": "regular",
                        "name": "Grey everyday tee",
                        "is_reference": True,
                        "measurements": {
                            "chest_width": m(52, "flatlay"),
                            "shoulder_width": m(46, "flatlay"),
                            "hem_width": m(51, "flatlay"),
                            "length": m(70, "flatlay"),
                            "sleeve_length": m(21, "flatlay", "medium"),
                            "bicep_width": m(19, "flatlay", "medium"),
                        },
                    },
                ),
                201,
            )
            ok(
                c.post(
                    "/v1/closet/garments",
                    headers=HEADERS,
                    json={
                        "kind": "sweater",
                        "cut": "raglan",
                        "stretch": "jersey_elastane",
                        "size_label": "L",
                        "fit_tag": "relaxed",
                        "name": "Navy crew knit",
                        "is_reference": False,
                        "measurements": {
                            "chest_width": m(58, "manual", "medium"),
                            "length": m(68, "manual", "medium"),
                        },
                    },
                ),
                201,
            )

            body = ok(
                c.post(
                    "/v1/body/records",
                    headers=HEADERS,
                    json={
                        "source": "manual",
                        "measurements": {
                            "height": m(178, "manual"),
                            "neck": m(39, "manual"),
                            "shoulder": m(45, "manual"),
                            "chest": m(98, "manual"),
                            "waist": m(84, "manual"),
                            "hip": m(98, "manual"),
                            "arm_length": m(62, "manual"),
                            "bicep": m(31, "manual"),
                            "back_length": m(46, "manual"),
                        },
                        "landmarks": {"waist_line_cm": 44, "hip_line_cm": 64, "wrist_cm": 78},
                    },
                ),
                201,
            )
            ok(c.post(f"/v1/body/records/{body['id']}/confirm", json={}, headers=HEADERS))

            product = ok(
                c.post(
                    "/v1/products/check",
                    headers=HEADERS,
                    json={"url": PRODUCT_URL, "garment_kind": "tee", "refresh": False},
                )
            )
            record("POST", "/v1/products/check", 200, product)
            report = ok(
                c.post("/v1/fit/reports", json={"product_id": product["id"]}, headers=HEADERS), 201
            )
            record("POST", "/v1/fit/reports", 201, report)

            outcome = ok(
                c.post(
                    "/v1/outcomes",
                    headers=HEADERS,
                    json={
                        "fit_report_id": report["id"],
                        "size_bought": report["report"]["pick"]["size_label"],
                        "kept": True,
                    },
                ),
                201,
            )
            record("POST", "/v1/outcomes", 201, outcome)

            # Reads, captured after the writes so they reflect the final state.
            for path in [
                "/v1/health",
                "/v1/me",
                "/v1/closet/garments",
                f"/v1/closet/garments/{tee['id']}",
                f"/v1/closet/garments/{tee['id']}/landmark-corrections",
                "/v1/body/records/current",
                f"/v1/body/records/{body['id']}",
                f"/v1/products/{product['id']}",
                "/v1/fit/reports",
                f"/v1/fit/reports/{report['id']}",
            ]:
                record("GET", path, 200, ok(c.get(path, headers=HEADERS)))

    text = json.dumps({"routes": routes}, indent=2, sort_keys=True)
    ids: dict[str, str] = {}

    def stable_id(match: re.Match[str]) -> str:
        return ids.setdefault(match.group(0), f"00000000-0000-4000-8000-{len(ids) + 1:012d}")

    text = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", stable_id, text)
    text = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?", "2026-10-19T09:00:00", text)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text + "\n")
    print(f"wrote {len(routes)} routes to {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
