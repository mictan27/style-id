from __future__ import annotations

import pytest
from chart_helpers import PAGE_IDS, load_page, make_extraction

from styleid_charts import (
    FakeExtractor,
    MemoryCache,
    StaticFetcher,
    extract_product,
    load_recorded,
)
from styleid_schema import ChartStatus, GarmentField, GarmentKind, Zone


@pytest.mark.parametrize("page_id", PAGE_IDS)
def test_labelled_pages_match_expected(page_id: str) -> None:
    html, expected, folder = load_page(page_id)
    extractor = FakeExtractor(
        default=load_recorded(folder / "extraction.json"), model_id="recorded"
    )
    result = extract_product(
        expected["url"],
        fetcher=StaticFetcher(html),
        extractor=extractor,
        garment_kind=GarmentKind(expected["garment_kind"]),
    )
    chart = result.chart
    assert result.title == expected["title"]
    assert chart.status.value == expected["status"]
    assert chart.classification.model_dump() == expected["classification"]
    assert (chart.stretch.value if chart.stretch else None) == expected["stretch"]
    assert chart.model_id == "recorded"
    assert [s.size_label for s in chart.sizes] == [s["size_label"] for s in expected["sizes"]]
    for got, want in zip(chart.sizes, expected["sizes"], strict=True):
        assert got.length_from_center_back == want["length_from_center_back"]
        assert got.sleeve_from_center_back == want["sleeve_from_center_back"]
        got_cells = {f.value: m.value_cm for f, m in got.measurements.items()}
        assert got_cells.keys() == want["measurements"].keys()
        for field, value in want["measurements"].items():
            assert got_cells[field] == pytest.approx(value, abs=0.5), (got.size_label, field)


def test_pipeline_uses_cache_and_skips_extractor_on_hit() -> None:
    html, expected, folder = load_page("acme_tee_flat_cm")
    extractor = FakeExtractor(default=load_recorded(folder / "extraction.json"))
    cache = MemoryCache()
    first = extract_product(
        expected["url"], fetcher=StaticFetcher(html), extractor=extractor, cache=cache
    )
    assert first.from_cache is False
    assert (
        first.canonical_url == "https://acme-apparel.example/products/heavyweight-tee?variant=123"
    )
    second = extract_product(
        expected["url"] + "&utm_medium=x",
        fetcher=StaticFetcher(html),
        extractor=extractor,
        cache=cache,
    )
    assert second.from_cache is True
    assert second.chart == first.chart
    assert len(extractor.calls) == 1


def test_pipeline_not_found_without_candidates() -> None:
    extractor = FakeExtractor()
    result = extract_product(
        "https://empty.example/p",
        fetcher=StaticFetcher("<html><body><h1>Hi</h1></body></html>"),
        extractor=extractor,
    )
    assert result.chart.status is ChartStatus.NOT_FOUND
    assert extractor.calls == []
    assert result.title == "Hi"
    assert result.brand_hint == "empty.example"


def test_pipeline_passes_typical_ease_for_body_charts() -> None:
    html, expected, _ = load_page("fjord_dl_ranges")
    ext = make_extraction(
        [("M", [("Chest", 98)])],
        chart_kind="body",
        measure_basis="unknown",
        fabric="100% linen",
        knit_or_woven="woven",
    )
    result = extract_product(
        expected["url"],
        fetcher=StaticFetcher(html),
        extractor=FakeExtractor(default=ext),
        garment_kind=GarmentKind.SHIRT,
        typical_ease={Zone.CHEST: 10.0},
    )
    assert result.chart.sizes[0].measurements[GarmentField.CHEST_WIDTH].value_cm == 54


def test_pipeline_flags_needs_review() -> None:
    html, expected, _ = load_page("acme_tee_flat_cm")
    ext = make_extraction([("S", [("Chest", 56)]), ("M", [("Chest", 53)])])
    result = extract_product(
        expected["url"], fetcher=StaticFetcher(html), extractor=FakeExtractor(default=ext)
    )
    assert result.chart.status is ChartStatus.NEEDS_REVIEW
    assert any("non-decreasing" in w for w in result.chart.warnings)
