from __future__ import annotations

from chart_helpers import make_extraction

from styleid_charts import check
from styleid_schema import (
    ChartClassification,
    GarmentField,
    GarmentKind,
    GarmentModel,
    MeasurementModel,
    Source,
    StretchClass,
)

CLS = ChartClassification(chart_kind="garment", measure_basis="flat", unit="cm")


def size(label: str, chest: float | None, length: float | None = None) -> GarmentModel:
    m: dict[GarmentField, MeasurementModel] = {}
    if chest is not None:
        m[GarmentField.CHEST_WIDTH] = MeasurementModel(value_cm=chest, source=Source.CHART)
    if length is not None:
        m[GarmentField.LENGTH] = MeasurementModel(value_cm=length, source=Source.CHART)
    return GarmentModel(
        kind=GarmentKind.TEE, stretch=StretchClass.COTTON_JERSEY, size_label=label, measurements=m
    )


def test_clean_chart_passes() -> None:
    result = check([size("S", 50, 70), size("M", 53, 72)], CLS)
    assert result.fails_hard is False
    assert result.warnings == []


def test_no_rows_is_hard() -> None:
    result = check([], CLS)
    assert result.fails_hard and "no sizes" in result.warnings[0]


def test_duplicate_labels_is_hard() -> None:
    result = check([size("M", 50), size("M", 53)], CLS)
    assert result.fails_hard
    assert any("duplicate" in w for w in result.warnings)


def test_chest_out_of_range_is_hard() -> None:
    assert check([size("S", 30)], CLS).fails_hard
    assert check([size("XXL", 95)], CLS).fails_hard
    assert not check([size("S", 35), size("XXL", 90)], CLS).fails_hard


def test_non_monotonic_chest_is_hard() -> None:
    result = check([size("S", 50), size("M", 56), size("L", 53)], CLS)
    assert result.fails_hard
    assert any("non-decreasing" in w for w in result.warnings)
    assert not check([size("S", 50), size("M", 50), size("L", 53)], CLS).fails_hard  # equal is fine


def test_zero_in_extraction_is_hard() -> None:
    ext = make_extraction([("M", [("Chest", 52), ("Hem", 0)])])
    result = check([size("M", 52)], CLS, extraction=ext)
    assert result.fails_hard
    assert any("zero" in w for w in result.warnings)


def test_soft_warnings() -> None:
    unknown = ChartClassification(chart_kind="unknown", measure_basis="unknown", unit="mixed")
    result = check([size("M", None, 30)], unknown)
    assert result.fails_hard is False
    joined = " ".join(result.warnings)
    assert "no chest width" in joined
    assert "implausible" in joined
    assert "chart kind" in joined
    assert "unit is mixed" in joined
