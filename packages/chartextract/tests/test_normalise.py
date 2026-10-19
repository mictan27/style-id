from __future__ import annotations

import pytest
from chart_helpers import make_extraction

from styleid_charts import (
    MEASURE_SYNONYMS,
    body_to_garment,
    map_measure,
    normalise,
    parse_value,
    stretch_class,
    to_cm,
)
from styleid_fit.thresholds import population_default_ease
from styleid_schema import (
    ChartExtraction,
    ChartStatus,
    Confidence,
    GarmentField,
    GarmentKind,
    Source,
    StretchClass,
    Zone,
)


@pytest.mark.parametrize(
    ("name", "field"),
    [
        ("Chest", GarmentField.CHEST_WIDTH),
        ("Chest (pit to pit)", GarmentField.CHEST_WIDTH),
        ("PIT-TO-PIT", GarmentField.CHEST_WIDTH),
        ("Bust", GarmentField.CHEST_WIDTH),
        ("Body Width (cm)", GarmentField.CHEST_WIDTH),
        ("1/2 Chest", GarmentField.CHEST_WIDTH),
        ("Width", GarmentField.CHEST_WIDTH),
        ("Length", GarmentField.LENGTH),
        ("Body length", GarmentField.LENGTH),
        ("HPS Length", GarmentField.LENGTH),
        ("Back Length", GarmentField.LENGTH),
        ("CB Length", GarmentField.LENGTH),
        ("Centre back length", GarmentField.LENGTH),
        ("Shoulder", GarmentField.SHOULDER_WIDTH),
        ("Across shoulder", GarmentField.SHOULDER_WIDTH),
        ("Shoulder width", GarmentField.SHOULDER_WIDTH),
        ("Sleeve", GarmentField.SLEEVE_LENGTH),
        ("Sleeve Length", GarmentField.SLEEVE_LENGTH),
        ("Sleeve length from CB", GarmentField.SLEEVE_LENGTH),
        ("Hem", GarmentField.HEM_WIDTH),
        ("Bottom", GarmentField.HEM_WIDTH),
        ("Sweep", GarmentField.HEM_WIDTH),
        ("Bottom width", GarmentField.HEM_WIDTH),
        ("Bicep", GarmentField.BICEP_WIDTH),
        ("Upper arm", GarmentField.BICEP_WIDTH),
        ("Sleeve width", GarmentField.BICEP_WIDTH),
        ("Arm", GarmentField.BICEP_WIDTH),
        ("Collar", GarmentField.COLLAR),
        ("Neck", GarmentField.COLLAR),
        ("Waist", GarmentField.WAIST_WIDTH),
    ],
)
def test_map_measure_synonyms(name: str, field: GarmentField) -> None:
    assert map_measure(name) is field


def test_map_measure_unknown_and_longest_match() -> None:
    assert map_measure("Price") is None
    assert map_measure("") is None
    assert map_measure("Shoulder width") is GarmentField.SHOULDER_WIDTH  # not generic "width"
    assert map_measure("Sleeve width") is GarmentField.BICEP_WIDTH  # not "sleeve"
    assert all(syn == syn.lower() for syns in MEASURE_SYNONYMS.values() for syn in syns)


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("52", 52.0),
        ("52,5", 52.5),
        ("96-100", 98.0),
        ("38/40", 39.0),
        ("96 " + chr(0x2013) + " 100", 98.0),
        ("20 to 22", 21.0),
        (54, 54.0),
        ("n/a", None),
        ("1 2 3", None),
    ],
)
def test_parse_value(text: str | float, value: float | None) -> None:
    assert parse_value(text) == value


def test_to_cm() -> None:
    assert to_cm(10, "in") == 25.4
    assert to_cm(10, "cm") == 10


def test_inches_converted() -> None:
    ext = make_extraction([("M", [("Chest", 20), ("Length", 28)])], unit="in")
    chart = normalise(ext)
    m = chart.sizes[0].measurements
    assert m[GarmentField.CHEST_WIDTH].value_cm == pytest.approx(50.8)
    assert m[GarmentField.LENGTH].value_cm == pytest.approx(71.12)
    assert m[GarmentField.CHEST_WIDTH].source is Source.CHART


def test_circumference_halved_only_for_width_fields() -> None:
    ext = make_extraction(
        [
            (
                "M",
                [
                    ("Chest", 104),
                    ("Hem", 100),
                    ("Waist", 96),
                    ("Bicep", 40),
                    ("Collar", 40),
                    ("Length", 70),
                    ("Shoulder", 46),
                ],
            )
        ],
        measure_basis="circumference",
    )
    m = normalise(ext).sizes[0].measurements
    assert m[GarmentField.CHEST_WIDTH].value_cm == 52
    assert m[GarmentField.HEM_WIDTH].value_cm == 50
    assert m[GarmentField.WAIST_WIDTH].value_cm == 48
    assert m[GarmentField.BICEP_WIDTH].value_cm == 20
    assert m[GarmentField.COLLAR].value_cm == 40
    assert m[GarmentField.LENGTH].value_cm == 70
    assert m[GarmentField.SHOULDER_WIDTH].value_cm == 46


def test_center_back_flags_from_model_fields_and_measure_names() -> None:
    ext = make_extraction(
        [("M", [("Chest", 52), ("CB Length", 68), ("Sleeve from CB", 80)])],
    )
    size = normalise(ext).sizes[0]
    assert size.length_from_center_back is True
    assert size.sleeve_from_center_back is True
    assert size.measurements[GarmentField.LENGTH].value_cm == 68  # not converted

    ext = make_extraction(
        [("M", [("Chest", 52), ("Length", 70)])],
        length_from="center_back",
        sleeve_from="shoulder_seam",
    )
    size = normalise(ext).sizes[0]
    assert size.length_from_center_back is True
    assert size.sleeve_from_center_back is False

    ext = make_extraction([("M", [("Chest", 52), ("Length (HPS)", 70)])])
    assert normalise(ext).sizes[0].length_from_center_back is False


def test_body_to_garment_uses_population_ease_by_default() -> None:
    body = {Zone.CHEST: 100.0, Zone.SHOULDER: 44.0, Zone.COLLAR: 38.0, Zone.SLEEVE: 60.0}
    out = body_to_garment(body, StretchClass.RIGID_WOVEN)
    chest_ease = population_default_ease(Zone.CHEST, StretchClass.RIGID_WOVEN)
    assert out[GarmentField.CHEST_WIDTH].value_cm == pytest.approx((100 + chest_ease) / 2)
    assert out[GarmentField.SHOULDER_WIDTH].value_cm == pytest.approx(
        44 + population_default_ease(Zone.SHOULDER, StretchClass.RIGID_WOVEN)
    )
    assert out[GarmentField.COLLAR].value_cm == pytest.approx(
        38 + population_default_ease(Zone.COLLAR, StretchClass.RIGID_WOVEN)
    )
    assert GarmentField.SLEEVE_LENGTH not in out  # position zones are not estimated
    for m in out.values():
        assert m.source is Source.BRAND_EASE_ESTIMATE
        assert m.confidence is Confidence.LOW


def test_body_to_garment_prefers_brand_ease() -> None:
    out = body_to_garment(
        {Zone.CHEST: 100.0, Zone.WAIST: 90.0}, StretchClass.COTTON_JERSEY, {Zone.CHEST: 8.0}
    )
    assert out[GarmentField.CHEST_WIDTH].value_cm == 54
    assert out[GarmentField.WAIST_WIDTH].value_cm == pytest.approx(
        (90 + population_default_ease(Zone.WAIST, StretchClass.COTTON_JERSEY)) / 2
    )


def test_body_chart_normalised_end_to_end() -> None:
    ext = make_extraction(
        [("M", [("Chest", 38), ("Neck", 15)]), ("L", [("Chest", 42), ("Neck", 16)])],
        chart_kind="body",
        measure_basis="unknown",
        unit="in",
        fabric="100% cotton poplin",
        knit_or_woven="woven",
    )
    chart = normalise(ext, garment_kind=GarmentKind.SHIRT)
    assert chart.status is ChartStatus.OK
    assert chart.classification.chart_kind == "body"
    assert chart.stretch is StretchClass.RIGID_WOVEN
    m = chart.sizes[0].measurements
    assert m[GarmentField.CHEST_WIDTH].value_cm == pytest.approx((38 * 2.54 + 14) / 2, abs=0.01)
    assert m[GarmentField.COLLAR].value_cm == pytest.approx(15 * 2.54 + 3, abs=0.01)
    assert any("estimates" in w for w in chart.warnings)


@pytest.mark.parametrize(
    ("fabric", "kow", "expected"),
    [
        ("100% cotton jersey", "unknown", StretchClass.COTTON_JERSEY),
        ("95% cotton 5% elastane", "knit", StretchClass.JERSEY_ELASTANE),
        ("92% cotton, 8% spandex", "unknown", None),  # no knit/woven signal at all
        ("97% cotton 3% lycra", "woven", StretchClass.WOVEN_ELASTANE),
        ("100% cotton poplin", "unknown", StretchClass.RIGID_WOVEN),
        ("Oxford cloth", "unknown", StretchClass.RIGID_WOVEN),
        ("100% linen", "unknown", StretchClass.RIGID_WOVEN),
        ("98% cotton 2% elastane twill", "unknown", StretchClass.WOVEN_ELASTANE),
        ("100% cotton 0% elastane jersey", "unknown", StretchClass.COTTON_JERSEY),
        ("100% cotton", "unknown", None),
        (None, "unknown", None),
        (None, "knit", StretchClass.COTTON_JERSEY),
        (None, "woven", StretchClass.RIGID_WOVEN),
    ],
)
def test_stretch_class(fabric: str | None, kow: str, expected: StretchClass | None) -> None:
    assert stretch_class(fabric, kow) is expected


def test_unknown_stretch_falls_back_with_warning() -> None:
    ext = make_extraction([("M", [("Chest", 52)])], fabric=None, knit_or_woven="unknown")
    chart = normalise(ext, garment_kind=GarmentKind.SHIRT)
    assert chart.stretch is None
    assert chart.sizes[0].stretch is StretchClass.RIGID_WOVEN
    assert any("assumed rigid_woven" in w for w in chart.warnings)


def test_unmapped_measures_and_zero_values() -> None:
    ext = make_extraction([("M", [("Chest", 52), ("Price", 30), ("Hem", 0)])])
    chart = normalise(ext)
    assert chart.unmapped_measures == ["Price"]
    assert GarmentField.HEM_WIDTH not in chart.sizes[0].measurements
    assert chart.status is ChartStatus.NEEDS_REVIEW  # zero value is a hard failure


def test_not_found_extraction() -> None:
    ext = make_extraction(
        [], found=False, chart_kind="unknown", measure_basis="unknown", unit="unknown"
    )
    chart = normalise(ext)
    assert chart.status is ChartStatus.NOT_FOUND
    assert chart.sizes == []


def test_mixed_basis_halves_only_large_widths() -> None:
    ext = make_extraction([("M", [("Chest", 104), ("Hem", 52)])], measure_basis="mixed")
    m = normalise(ext).sizes[0].measurements
    assert m[GarmentField.CHEST_WIDTH].value_cm == 52
    assert m[GarmentField.HEM_WIDTH].value_cm == 52


def test_normalise_round_trips_through_json(flat_tee: ChartExtraction) -> None:
    chart = normalise(flat_tee, model_id="test-model")
    assert chart.model_id == "test-model"
    dumped = chart.model_dump_json()
    assert type(chart).model_validate_json(dumped) == chart
