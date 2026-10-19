from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from styleid_schema import ChartCell, ChartExtraction, ChartRow, Confidence

LABELLED_DIR = Path(__file__).resolve().parents[1] / "eval" / "labelled"
PAGE_IDS = sorted(p.name for p in LABELLED_DIR.iterdir() if p.is_dir())


def cell(measure: str, value: float, unit: str | None = None) -> ChartCell:
    return ChartCell(measure=measure, value=value, unit=unit)


def make_extraction(
    rows: list[tuple[str, list[tuple[str, float]]]],
    *,
    chart_kind: str = "garment",
    measure_basis: str = "flat",
    unit: str = "cm",
    fabric: str | None = "100% cotton jersey",
    knit_or_woven: str = "knit",
    length_from: str = "unknown",
    sleeve_from: str = "unknown",
    found: bool = True,
    notes: str | None = None,
) -> ChartExtraction:
    return ChartExtraction(
        found=found,
        chart_kind=chart_kind,
        measure_basis=measure_basis,
        unit=unit,
        rows=[
            ChartRow(size_label=label, cells=[cell(m, v) for m, v in cells])
            for label, cells in rows
        ],
        fabric_composition=fabric,
        knit_or_woven=knit_or_woven,
        length_from=length_from,
        sleeve_from=sleeve_from,
        notes=notes,
        confidence=Confidence.HIGH,
    )


def load_page(page_id: str) -> tuple[str, dict[str, Any], Path]:
    folder = LABELLED_DIR / page_id
    html = (folder / "page.html").read_text("utf-8")
    expected = json.loads((folder / "expected.json").read_text("utf-8"))
    return html, expected, folder
