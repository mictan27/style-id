"""Decide what kind of chart the model extracted, overriding its claims with value-range rules."""

from __future__ import annotations

import re
import statistics
from typing import Literal

from styleid_schema import ChartClassification, ChartExtraction

ChartKind = Literal["body", "garment", "unknown"]
Basis = Literal["flat", "circumference", "mixed", "unknown"]
Unit = Literal["cm", "in", "mixed", "unknown"]

_CHEST_NAME = re.compile(r"chest|bust|pit|body width|half chest", re.IGNORECASE)
_INCH_HINT = re.compile(r"\binch(es)?\b|\d\s*(?:in\b|\")", re.IGNORECASE)
_IN_TO_CM = 2.54


def chest_values(extraction: ChartExtraction) -> list[float]:
    """Raw values of every cell whose measure name looks like chest/bust."""
    return [
        cell.value
        for row in extraction.rows
        for cell in row.cells
        if _CHEST_NAME.search(cell.measure) and cell.value > 0
    ]


def _all_values(extraction: ChartExtraction) -> list[float]:
    """Every positive numeric value in the chart."""
    return [c.value for r in extraction.rows for c in r.cells if c.value > 0]


def _cell_units(extraction: ChartExtraction) -> set[str]:
    """Distinct per-cell units the model reported."""
    return {c.unit for r in extraction.rows for c in r.cells if c.unit is not None}


def classify_unit(extraction: ChartExtraction, page_text: str | None = None) -> Unit:
    """Resolve the unit: model claim, then per-cell units, then small-values-plus-inch-hint."""
    unit: Unit = extraction.unit
    cell_units = _cell_units(extraction)
    if unit in ("unknown", "mixed") and len(cell_units) == 1:
        unit = "cm" if cell_units == {"cm"} else "in"
    if unit == "unknown" and len(cell_units) > 1:
        unit = "mixed"
    values = _all_values(extraction)
    if (
        unit == "unknown"
        and values
        and max(values) < 60
        and page_text
        and _INCH_HINT.search(page_text)
    ):
        unit = "in"
    if unit == "unknown" and values and max(values) < 30:
        unit = "in"  # no top is under 30 cm in any dimension
    return unit


def classify(extraction: ChartExtraction, *, page_text: str | None = None) -> ChartClassification:
    """Start from the model's fields and override with chest value-range rules."""
    kind: ChartKind = extraction.chart_kind
    basis: Basis = extraction.measure_basis
    unit = classify_unit(extraction, page_text)

    chest = chest_values(extraction)
    if chest:
        factor = _IN_TO_CM if unit == "in" else 1.0
        median = statistics.median(v * factor for v in chest)
        if 40 <= median <= 70:
            kind, basis = "garment", "flat"
        elif 80 <= median <= 130 and kind != "garment":
            kind, basis = "body", "circumference"
        elif median >= 75 and kind == "garment" and basis != "mixed":
            basis = "circumference"  # a flat width this large is impossible for a top
    if kind == "body":
        basis = "circumference"
    return ChartClassification(chart_kind=kind, measure_basis=basis, unit=unit)
