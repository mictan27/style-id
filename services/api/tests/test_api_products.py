from pathlib import Path
from typing import Any

import pytest
from conftest import DEV_HEADERS, build_app, check_product, make_settings
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from styleid_api.db.models import Garment, Product, SizeChart
from styleid_schema import GarmentKind, NormalisedChart


def count(app: FastAPI, model: type[Any], **where: Any) -> int:
    with app.state.session_factory() as db:
        stmt = select(func.count()).select_from(model)
        for key, value in where.items():
            stmt = stmt.where(getattr(model, key) == value)
        return int(db.scalar(stmt) or 0)


def test_check_extracts_chart_and_materialises_sizes(client: TestClient, app: FastAPI) -> None:
    product = check_product(client, "https://www.Shop.example.com/products/tee/?utm_source=ig")
    assert product["url_canonical"] == "https://shop.example.com/products/tee"
    assert product["brand"]["domain"] == "shop.example.com"
    assert product["garment_kind"] == "tee"
    assert product["stretch_class"] == "cotton_jersey"
    assert product["fabric_composition"] == "100% cotton"
    chart = product["chart"]
    assert chart["status"] == "ok"
    assert chart["size_labels"] == ["S", "M", "L"]
    assert chart["model_id"] == "fake-extractor"
    assert count(app, Garment, product_id=product["id"]) == 3

    got = client.get(f"/v1/products/{product['id']}", headers=DEV_HEADERS)
    assert got.status_code == 200 and got.json()["chart"]["id"] == chart["id"]


def test_same_url_with_other_tracking_params_hits_same_product(
    client: TestClient, app: FastAPI
) -> None:
    a = check_product(client, "https://shop.example.com/products/tee?utm_source=x&fbclid=1")
    b = check_product(client, "https://shop.example.com/products/tee/?gclid=abc")
    c = check_product(client, "http://www.shop.example.com:80/products/tee#reviews")
    assert a["id"] == b["id"] == c["id"]
    assert a["chart"]["id"] == b["chart"]["id"] == c["chart"]["id"]
    assert count(app, Product) == 1
    assert count(app, SizeChart) == 1
    assert count(app, Garment, product_id=a["id"]) == 3


def test_distinct_query_params_are_distinct_products(client: TestClient) -> None:
    a = check_product(client, "https://shop.example.com/products?id=1")
    b = check_product(client, "https://shop.example.com/products?id=2")
    assert a["id"] != b["id"]


def test_failed_extraction_is_recorded_and_retried(
    tmp_path: Path, jwks_store: dict[str, Any]
) -> None:
    attempts = 0

    def flaky(url: str, kind: GarmentKind) -> NormalisedChart:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("page timed out")

    app = build_app(make_settings(tmp_path), jwks_store, extract_fn=flaky)
    with TestClient(app) as client:
        product = check_product(client)
        assert product["chart"]["status"] == "failed"
        assert "page timed out" in product["chart"]["error"]
        assert product["stretch_class"] is None
        # A failed chart is retried on the next check.
        check_product(client)
        assert attempts == 2
        assert count(app, SizeChart, product_id=product["id"]) == 2


def test_check_rejects_url_without_host(client: TestClient) -> None:
    r = client.post("/v1/products/check", json={"url": "tee-shirt"}, headers=DEV_HEADERS)
    assert r.status_code == 422


def test_default_extract_reports_missing_package_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    from styleid_api.jobs.extraction import ExtractionUnavailable, make_default_extract

    # A None entry in sys.modules makes `import styleid_charts` raise ImportError.
    monkeypatch.setitem(sys.modules, "styleid_charts", None)
    with pytest.raises(ExtractionUnavailable, match="not importable"):
        make_default_extract("claude-test")("https://x.example/p", GarmentKind.TEE)
