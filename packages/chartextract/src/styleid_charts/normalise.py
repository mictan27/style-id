"""Turn a ChartExtraction into per-size GarmentModels, all flat widths in cm.

Handles vendor measure names, inches, circumference-vs-flat, ranges, centre-back flags,
body charts (converted to garment estimates with brand or population ease) and stretch class.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from styleid_fit.thresholds import population_default_ease
from styleid_fit.types import ZONE_SPECS, ZoneKind
from styleid_schema import (
    ChartClassification,
    ChartExtraction,
    ChartStatus,
    Confidence,
    Cut,
    GarmentField,
    GarmentKind,
    GarmentModel,
    MeasurementModel,
    NormalisedChart,
    Source,
    StretchClass,
    Zone,
)

from .classify import classify
from .sanity import check

IN_TO_CM = 2.54

MEASURE_SYNONYMS: dict[GarmentField, tuple[str, ...]] = {
    GarmentField.CHEST_WIDTH: (
        "chest",
        "chest width",
        "pit to pit",
        "pit-to-pit",
        "p2p",
        "armpit to armpit",
        "underarm to underarm",
        "bust",
        "body width",
        "width",
        "half chest",
        "1/2 chest",
        "across chest",
        "chest circumference",
        "bust circumference",
    ),
    GarmentField.WAIST_WIDTH: (
        "waist",
        "waist width",
        "half waist",
        "1/2 waist",
        "waist circumference",
    ),
    GarmentField.HEM_WIDTH: (
        "hem",
        "hem width",
        "bottom",
        "bottom width",
        "sweep",
        "bottom hem",
        "hem sweep",
        "hip",
        "hips",
        "hip width",
        "hip circumference",
        "seat",
    ),
    GarmentField.BICEP_WIDTH: (
        "bicep",
        "biceps",
        "bicep width",
        "upper arm",
        "upper arm width",
        "sleeve width",
        "arm",
        "arm width",
        "arm circumference",
        "sleeve opening",
    ),
    GarmentField.SHOULDER_WIDTH: (
        "shoulder",
        "shoulders",
        "across shoulder",
        "across shoulders",
        "shoulder width",
        "shoulder to shoulder",
        "shoulder seam to seam",
    ),
    GarmentField.SLEEVE_LENGTH: (
        "sleeve",
        "sleeves",
        "sleeve length",
        "arm length",
        "sleeve length from cb",
        "sleeve from cb",
        "sleeve length from center back",
        "sleeve length from centre back",
    ),
    GarmentField.LENGTH: (
        "length",
        "body length",
        "hps length",
        "length from hps",
        "back length",
        "cb length",
        "center back length",
        "centre back length",
        "total length",
        "front length",
        "garment length",
        "length from shoulder",
    ),
    GarmentField.COLLAR: (
        "collar",
        "neck",
        "neck width",
        "neck circumference",
        "collar size",
        "neckline",
    ),
}

#: Width fields whose circumference is halved to a flat width.
_HALVED: frozenset[GarmentField] = frozenset(
    {
        GarmentField.CHEST_WIDTH,
        GarmentField.WAIST_WIDTH,
        GarmentField.HEM_WIDTH,
        GarmentField.BICEP_WIDTH,
    }
)
_UNIT_TOKENS = frozenset({"cm", "cms", "in", "inch", "inches", "mm"})
_CB_HINT = re.compile(r"\b(cb|center back|centre back)\b")
_RANGE = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*(?:[-/\u2013\u2014]|to)\s*(\d+(?:[.,]\d+)?)\s*$")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")

_FIELD_TO_ZONE: dict[GarmentField, Zone] = {spec.garment_field: z for z, spec in ZONE_SPECS.items()}
_SYNONYM_INDEX: list[tuple[str, GarmentField]] = sorted(
    ((syn, field) for field, syns in MEASURE_SYNONYMS.items() for syn in syns),
    key=lambda item: len(item[0]),
    reverse=True,
)

_DEFAULT_STRETCH: dict[GarmentKind, StretchClass] = {
    GarmentKind.TEE: StretchClass.COTTON_JERSEY,
    GarmentKind.SWEATER: StretchClass.COTTON_JERSEY,
    GarmentKind.HOODIE: StretchClass.COTTON_JERSEY,
    GarmentKind.SHIRT: StretchClass.RIGID_WOVEN,
}


def normalise_name(name: str) -> str:
    """Lower-case, strip punctuation and unit tokens, collapse spaces."""
    lowered = re.sub(r"[^a-z0-9/ ]+", " ", name.lower().replace("-", " "))
    tokens = [t for t in lowered.split() if t not in _UNIT_TOKENS]
    return " ".join(tokens)


def map_measure(name: str) -> GarmentField | None:
    """Map a vendor measure name to a GarmentField; longest matching synonym wins."""
    cleaned = normalise_name(name)
    if not cleaned:
        return None
    for syn, field in _SYNONYM_INDEX:
        if cleaned == syn:
            return field
    padded = f" {cleaned} "
    for syn, field in _SYNONYM_INDEX:
        if f" {syn} " in padded:
            return field
    return None


def parse_value(text: str | float) -> float | None:
    """Parse '52', '52,5', '96-100' or '38/40' (ranges become the midpoint)."""
    if isinstance(text, int | float):
        return float(text)
    m = _RANGE.match(text)
    if m:
        lo, hi = (float(g.replace(",", ".")) for g in m.groups())
        return (lo + hi) / 2
    numbers = _NUMBER.findall(text)
    if len(numbers) == 1:
        return float(numbers[0].replace(",", "."))
    return None


def to_cm(value: float, unit: str) -> float:
    """Convert a value to centimetres."""
    return round(value * IN_TO_CM, 2) if unit == "in" else value


def stretch_class(fabric_composition: str | None, knit_or_woven: str) -> StretchClass | None:
    """Infer the stretch class from fabric words; None when there is not enough to go on."""
    text = (fabric_composition or "").lower()
    elastane = bool(re.search(r"elastane|spandex|lycra|elastan|stretch", text))
    if m := re.search(r"(\d+(?:\.\d+)?)\s*%\s*(elastane|spandex|lycra|elastan)", text):
        elastane = float(m.group(1)) > 0
    knit = knit_or_woven == "knit" or bool(
        re.search(r"jersey|knit|tee|t-shirt|rib|fleece|french terry|interlock|pique|piqu", text)
    )
    woven = knit_or_woven == "woven" or bool(
        re.search(r"woven|poplin|oxford|twill|denim|linen|chambray|flannel|canvas|broadcloth", text)
    )
    if knit and not woven:
        return StretchClass.JERSEY_ELASTANE if elastane else StretchClass.COTTON_JERSEY
    if woven:
        return StretchClass.WOVEN_ELASTANE if elastane else StretchClass.RIGID_WOVEN
    return None


def body_to_garment(
    body_values_by_zone: Mapping[Zone, float],
    stretch: StretchClass,
    typical_ease: Mapping[Zone, float] | None = None,
) -> dict[GarmentField, MeasurementModel]:
    """Estimate flat garment measurements from body measurements plus ease."""
    out: dict[GarmentField, MeasurementModel] = {}
    for zone, body in body_values_by_zone.items():
        spec = ZONE_SPECS[zone]
        if spec.kind is ZoneKind.POSITION or body <= 0:
            continue
        ease = (
            typical_ease[zone]
            if typical_ease is not None and zone in typical_ease
            else population_default_ease(zone, stretch)
        )
        garment = body + ease
        if spec.kind is ZoneKind.CIRCUMFERENCE:
            garment /= 2
        out[spec.garment_field] = MeasurementModel(
            value_cm=round(garment, 2), source=Source.BRAND_EASE_ESTIMATE, confidence=Confidence.LOW
        )
    return out


def _cell_unit(cell_unit: str | None, chart_unit: str) -> str:
    """Pick the unit for one cell: its own if given, else the chart's (unknown -> cm)."""
    if cell_unit:
        return cell_unit
    return "in" if chart_unit == "in" else "cm"


def normalise(
    extraction: ChartExtraction,
    *,
    garment_kind: GarmentKind = GarmentKind.TEE,
    typical_ease: Mapping[Zone, float] | None = None,
    classification: ChartClassification | None = None,
    page_text: str | None = None,
    model_id: str | None = None,
) -> NormalisedChart:
    """Classify, convert and sanity-check an extraction into a NormalisedChart."""
    cls = classification or classify(extraction, page_text=page_text)
    stretch = stretch_class(extraction.fabric_composition, extraction.knit_or_woven)
    warnings: list[str] = []
    if extraction.notes:
        warnings.append(f"model note: {extraction.notes}")
    if not extraction.found or not extraction.rows:
        return NormalisedChart(
            status=ChartStatus.NOT_FOUND,
            classification=cls,
            stretch=stretch,
            fabric_composition=extraction.fabric_composition,
            warnings=warnings,
            model_id=model_id,
        )

    effective_stretch = stretch
    if effective_stretch is None:
        effective_stretch = _DEFAULT_STRETCH[garment_kind]
        warnings.append(f"stretch class unknown from fabric; assumed {effective_stretch.value}")
    if cls.unit == "unknown":
        warnings.append("unit unknown; values treated as cm")
    if cls.measure_basis == "mixed":
        warnings.append("mixed basis: widths above 75 cm were treated as circumferences")

    confidence = Confidence.LOW if cls.chart_kind == "unknown" else extraction.confidence
    unmapped: list[str] = []
    length_cb = extraction.length_from == "center_back"
    sleeve_cb = extraction.sleeve_from == "center_back"
    sizes: list[GarmentModel] = []

    for row in extraction.rows:
        measurements: dict[GarmentField, MeasurementModel] = {}
        body_by_zone: dict[Zone, float] = {}
        for cell in row.cells:
            field = map_measure(cell.measure)
            if field is None:
                if cell.measure not in unmapped:
                    unmapped.append(cell.measure)
                continue
            if cell.value <= 0:
                warnings.append(f"size {row.size_label}: {cell.measure} is {cell.value}; skipped")
                continue
            value_cm = to_cm(cell.value, _cell_unit(cell.unit, cls.unit))
            lowered = cell.measure.lower().replace("-", " ")
            if field is GarmentField.LENGTH and _CB_HINT.search(lowered):
                length_cb = True
            if field is GarmentField.SLEEVE_LENGTH and _CB_HINT.search(lowered):
                sleeve_cb = True
            if cls.chart_kind == "body":
                zone = _FIELD_TO_ZONE[field]
                body_by_zone.setdefault(zone, value_cm)
                continue
            if field in _HALVED and (
                cls.measure_basis == "circumference"
                or (cls.measure_basis == "mixed" and value_cm > 75)
            ):
                value_cm = round(value_cm / 2, 2)
            measurements.setdefault(
                field,
                MeasurementModel(value_cm=value_cm, source=Source.CHART, confidence=confidence),
            )
        if cls.chart_kind == "body":
            measurements = body_to_garment(body_by_zone, effective_stretch, typical_ease)
        if not measurements:
            warnings.append(f"size {row.size_label}: no usable measurements")
            continue
        sizes.append(
            GarmentModel(
                kind=garment_kind,
                cut=extraction.cut or Cut.SET_IN,
                stretch=effective_stretch,
                size_label=row.size_label,
                length_from_center_back=length_cb,
                sleeve_from_center_back=sleeve_cb,
                measurements=measurements,
            )
        )

    if cls.chart_kind == "body":
        warnings.append("body chart: garment values are estimates from body size plus ease")
    if unmapped:
        warnings.append(f"unmapped measures: {', '.join(unmapped)}")

    sanity = check(sizes, cls, extraction=extraction)
    warnings.extend(sanity.warnings)
    status = (
        ChartStatus.NEEDS_REVIEW
        if sanity.fails_hard or cls.chart_kind == "unknown"
        else ChartStatus.OK
    )
    return NormalisedChart(
        status=status,
        classification=cls,
        stretch=stretch,
        fabric_composition=extraction.fabric_composition,
        sizes=sizes,
        warnings=warnings,
        model_id=model_id,
        unmapped_measures=unmapped,
    )
