from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from styleid_fit import (
    Body,
    BodyField,
    Confidence,
    Cut,
    Garment,
    GarmentField,
    GarmentKind,
    Label,
    Landmarks,
    Measurement,
    Source,
    StretchClass,
)

GOLDEN_DIR = Path(__file__).parent / "golden"


def m(
    value: float, source: Source = Source.MANUAL, conf: Confidence = Confidence.HIGH
) -> Measurement:
    return Measurement(value, source, conf)


def garment(
    *,
    kind: GarmentKind = GarmentKind.TEE,
    cut: Cut = Cut.SET_IN,
    stretch: StretchClass = StretchClass.COTTON_JERSEY,
    size_label: str | None = None,
    fit_tag: Label | None = None,
    source: Source = Source.FLATLAY,
    conf: Confidence = Confidence.HIGH,
    **fields: float,
) -> Garment:
    return Garment(
        kind=kind,
        cut=cut,
        stretch=stretch,
        size_label=size_label,
        fit_tag=fit_tag,
        measurements={GarmentField(k): m(v, source, conf) for k, v in fields.items()},
    )


def body(
    *,
    source: Source = Source.LIDAR,
    conf: Confidence = Confidence.HIGH,
    landmarks: Landmarks | None = None,
    **fields: float,
) -> Body:
    return Body(
        measurements={BodyField(k): m(v, source, conf) for k, v in fields.items()},
        landmarks=landmarks,
    )


@pytest.fixture
def grey_tee() -> Garment:
    """The user's favourite tee: cotton jersey M, chest flat 50 cm (100 cm around)."""
    return garment(
        size_label="M",
        fit_tag=Label.REGULAR,
        chest_width=50,
        shoulder_width=44,
        hem_width=49,
        bicep_width=18,
        length=70,
        sleeve_length=20,
    )


@pytest.fixture
def avg_body() -> Body:
    return body(
        height=178,
        neck=39,
        shoulder=44,
        chest=96,
        waist=84,
        hip=98,
        arm_length=62,
        bicep=31,
        back_length=46,
    )


def load_garment(d: dict[str, Any]) -> Garment:
    return garment(
        kind=GarmentKind(d.get("kind", "tee")),
        cut=Cut(d.get("cut", "set_in")),
        stretch=StretchClass(d.get("stretch", "cotton_jersey")),
        size_label=d.get("size_label"),
        fit_tag=Label(d["fit_tag"]) if d.get("fit_tag") else None,
        source=Source(d.get("source", "flatlay")),
        conf=Confidence(d.get("confidence", "high")),
        **d["measurements"],
    )


def load_body(d: dict[str, Any] | None) -> Body | None:
    if d is None:
        return None
    lm = d.get("landmarks")
    return body(
        source=Source(d.get("source", "lidar")),
        conf=Confidence(d.get("confidence", "high")),
        landmarks=Landmarks(**lm) if lm else None,
        **d["measurements"],
    )


def golden_cases() -> list[tuple[str, dict[str, Any]]]:
    return [(p.stem, json.loads(p.read_text())) for p in sorted(GOLDEN_DIR.glob("*.json"))]
