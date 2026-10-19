"""Plausibility checks on normalised sizes. Hard failures send the chart to review."""

from __future__ import annotations

import itertools
from collections import Counter
from dataclasses import dataclass, field

from styleid_schema import ChartClassification, ChartExtraction, GarmentField, GarmentModel

CHEST_MIN_CM = 35.0
CHEST_MAX_CM = 90.0
LENGTH_MIN_CM = 40.0
LENGTH_MAX_CM = 110.0


@dataclass(frozen=True)
class SanityResult:
    """Warnings plus whether any of them is a hard failure."""

    warnings: list[str] = field(default_factory=list)
    fails_hard: bool = False


def _chest(size: GarmentModel) -> float | None:
    """Flat chest width of a size, if present."""
    m = size.measurements.get(GarmentField.CHEST_WIDTH)
    return None if m is None else m.value_cm


def check(
    sizes: list[GarmentModel],
    classification: ChartClassification,
    *,
    extraction: ChartExtraction | None = None,
) -> SanityResult:
    """Run every rule and collect warnings; `fails_hard` is set by any hard rule."""
    warnings: list[str] = []
    hard = False

    if len(sizes) < 1:
        return SanityResult(["no sizes after normalisation"], True)

    labels = [s.size_label or "" for s in sizes]
    dupes = sorted(label for label, n in Counter(labels).items() if n > 1)
    if dupes:
        warnings.append(f"duplicate size labels: {', '.join(dupes)}")
        hard = True

    if extraction is not None:
        zeros = [
            f"{row.size_label}/{cell.measure}"
            for row in extraction.rows
            for cell in row.cells
            if cell.value == 0
        ]
        if zeros:
            warnings.append(f"zero values in chart: {', '.join(zeros)}")
            hard = True

    chests = [(s.size_label, _chest(s)) for s in sizes]
    for label, chest in chests:
        if chest is not None and not CHEST_MIN_CM <= chest <= CHEST_MAX_CM:
            warnings.append(f"size {label}: flat chest {chest:.1f} cm outside 35-90 cm")
            hard = True
    present = [c for _, c in chests if c is not None]
    if present and any(b < a for a, b in itertools.pairwise(present)):
        warnings.append("chest width is not non-decreasing in page row order")
        hard = True
    if not present:
        warnings.append("no chest width in any size")

    for size in sizes:
        length = size.measurements.get(GarmentField.LENGTH)
        if length is not None and not LENGTH_MIN_CM <= length.value_cm <= LENGTH_MAX_CM:
            warnings.append(f"size {size.size_label}: length {length.value_cm:.1f} cm implausible")

    if classification.chart_kind == "unknown":
        warnings.append("chart kind could not be determined")
    if classification.unit in ("unknown", "mixed"):
        warnings.append(f"unit is {classification.unit}")

    return SanityResult(warnings, hard)
