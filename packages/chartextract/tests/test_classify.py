from __future__ import annotations

from chart_helpers import make_extraction

from styleid_charts import classify, classify_unit


def test_model_fields_kept_when_plausible() -> None:
    ext = make_extraction([("M", [("Chest", 52), ("Length", 70)])])
    cls = classify(ext)
    assert (cls.chart_kind, cls.measure_basis, cls.unit) == ("garment", "flat", "cm")


def test_body_range_overrides_unknown_kind() -> None:
    ext = make_extraction(
        [("M", [("Chest", 98)]), ("L", [("Chest", 106)])],
        chart_kind="unknown",
        measure_basis="unknown",
    )
    cls = classify(ext)
    assert (cls.chart_kind, cls.measure_basis) == ("body", "circumference")


def test_small_values_override_body_claim_to_garment_flat() -> None:
    ext = make_extraction([("M", [("Bust", 52)])], chart_kind="body", measure_basis="unknown")
    cls = classify(ext)
    assert (cls.chart_kind, cls.measure_basis) == ("garment", "flat")


def test_large_garment_values_become_circumference() -> None:
    ext = make_extraction([("M", [("Chest", 104)])], chart_kind="garment", measure_basis="flat")
    assert classify(ext).measure_basis == "circumference"


def test_inches_detected_from_small_values_and_page_text() -> None:
    ext = make_extraction(
        [("M", [("Chest", 39), ("Length", 28)])], unit="unknown", chart_kind="body"
    )
    assert classify_unit(ext, 'All measurements in inches (")') == "in"
    assert classify_unit(ext, "Measurements in centimetres") == "unknown"
    # with unit resolved to inches, 39 in = 99 cm -> body chart
    assert classify(ext, page_text="inches").chart_kind == "body"


def test_unit_from_consistent_cell_units() -> None:
    ext = make_extraction([("M", [("Chest", 20.5)])], unit="unknown")
    ext = ext.model_copy(
        update={
            "rows": [
                r.model_copy(
                    update={"cells": [c.model_copy(update={"unit": "in"}) for c in r.cells]}
                )
                for r in ext.rows
            ]
        }
    )
    assert classify_unit(ext) == "in"


def test_tiny_values_are_inches_even_without_hint() -> None:
    ext = make_extraction([("M", [("Chest", 20.5), ("Length", 27)])], unit="unknown")
    assert classify_unit(ext) == "in"


def test_unknown_kept_when_rules_cannot_decide() -> None:
    ext = make_extraction(
        [("M", [("Length", 70)])], chart_kind="unknown", measure_basis="unknown", unit="unknown"
    )
    cls = classify(ext)
    assert (cls.chart_kind, cls.measure_basis, cls.unit) == ("unknown", "unknown", "unknown")
