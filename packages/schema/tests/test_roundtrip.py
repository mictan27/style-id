import json

from styleid_fit import build_report
from styleid_fit.types import Body, BodyField, Garment, GarmentField, Measurement
from styleid_schema import (
    BodyModel,
    ChartExtraction,
    Confidence,
    Cut,
    FitReportModel,
    GarmentKind,
    GarmentModel,
    LandmarksModel,
    MeasurementModel,
    OutcomeModel,
    PreferencesModel,
    Source,
    StretchClass,
    Zone,
)


def tee(size: str, chest: float) -> GarmentModel:
    return GarmentModel(
        kind=GarmentKind.TEE,
        stretch=StretchClass.COTTON_JERSEY,
        size_label=size,
        measurements={
            GarmentField.CHEST_WIDTH: MeasurementModel(value_cm=chest, source=Source.CHART),
            GarmentField.LENGTH: MeasurementModel(value_cm=70, source=Source.CHART),
        },
    )


def test_garment_roundtrip_through_engine_and_json():
    g = tee("M", 50)
    engine = g.to_engine()
    assert isinstance(engine, Garment)
    assert engine.measurements[GarmentField.CHEST_WIDTH] == Measurement(50, Source.CHART)
    back = GarmentModel.from_engine(engine)
    assert back == g
    as_json = json.loads(g.model_dump_json())
    assert as_json["measurements"]["chest_width"]["value_cm"] == 50
    assert GarmentModel.model_validate(as_json) == g


def test_body_roundtrip():
    b = BodyModel(
        source=Source.LIDAR,
        measurements={BodyField.CHEST: MeasurementModel(value_cm=96, source=Source.LIDAR)},
        landmarks=LandmarksModel(waist_line_cm=46, hip_line_cm=64, wrist_cm=62),
    )
    engine = b.to_engine()
    assert isinstance(engine, Body)
    assert engine.landmarks is not None and engine.landmarks.hip_line_cm == 64
    assert BodyModel.from_engine(engine, Source.LIDAR) == b


def test_fit_report_serialises():
    ref = GarmentModel(
        kind=GarmentKind.TEE,
        stretch=StretchClass.COTTON_JERSEY,
        size_label="M",
        measurements={
            GarmentField.CHEST_WIDTH: MeasurementModel(value_cm=50, source=Source.FLATLAY),
            GarmentField.LENGTH: MeasurementModel(value_cm=70, source=Source.FLATLAY),
        },
    )
    run = [tee("S", 48), tee("M", 50), tee("L", 52)]
    report = build_report([g.to_engine() for g in run], None, [ref.to_engine()])
    model = FitReportModel.from_engine(report)
    assert model.pick is not None and model.pick.size_label == "M"
    data = json.loads(model.model_dump_json())
    assert data["pick"]["zones"][0]["zone"] == "chest"
    assert data["pick"]["zones"][0]["basis"] == "reference"
    assert FitReportModel.model_validate(data) == model


def test_preferences_and_outcome_convert():
    p = PreferencesModel(shift_cm={Zone.CHEST: 1.0})
    assert p.to_engine().shift(Zone.CHEST) == 1.0
    assert PreferencesModel.from_engine(p.to_engine()) == p
    o = OutcomeModel(kept=False, zone=Zone.CHEST, direction="tight")
    assert o.to_engine().zone is Zone.CHEST


def test_chart_extraction_schema_is_strict_enough_for_structured_output():
    schema = ChartExtraction.model_json_schema()
    assert schema["required"] == ["found", "chart_kind", "measure_basis", "unit", "confidence"]
    ex = ChartExtraction(
        found=True,
        chart_kind="garment",
        measure_basis="flat",
        unit="cm",
        rows=[{"size_label": "M", "cells": [{"measure": "Chest", "value": 50}]}],
        cut=Cut.SET_IN,
        confidence=Confidence.HIGH,
    )
    assert ex.rows[0].cells[0].unit is None


def test_measurement_rejects_nonsense():
    import pytest

    with pytest.raises(ValueError):
        MeasurementModel(value_cm=0, source=Source.MANUAL)
    with pytest.raises(ValueError):
        MeasurementModel(value_cm=500, source=Source.MANUAL)
