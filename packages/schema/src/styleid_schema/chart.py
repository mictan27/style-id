"""Size-chart extraction schemas.

`ChartExtraction` is what Claude is asked to produce (structured output) from a
product page. `NormalisedChart` is what the pipeline stores after classification,
sanity checks and unit conversion: one GarmentModel per size, all in cm.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from styleid_fit.types import Confidence, Cut, StretchClass

from .garment import GarmentModel


class ChartCell(BaseModel):
    model_config = ConfigDict(frozen=True)

    measure: str = Field(description="Measurement name exactly as the page labels it")
    value: float
    unit: Literal["cm", "in"] | None = Field(
        default=None, description="Unit for this cell if the page states one; else null"
    )


class ChartRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    size_label: str = Field(description="Size exactly as labelled, e.g. 'M', '40', 'L/XL'")
    cells: list[ChartCell]


class ChartExtraction(BaseModel):
    """Structured output requested from the model. Keep field descriptions precise: they are
    the prompt."""

    model_config = ConfigDict(frozen=True)

    found: bool = Field(description="False when the page has no size chart at all")
    chart_kind: Literal["body", "garment", "unknown"] = Field(
        description=(
            "'garment' when the numbers are of the garment itself (laid flat or around); "
            "'body' when they describe the wearer's body (e.g. 'fits chest 96-100')"
        )
    )
    measure_basis: Literal["flat", "circumference", "mixed", "unknown"] = Field(
        description=(
            "For garment charts: 'flat' when widths are measured across the garment lying flat "
            "(pit to pit), 'circumference' when they are all the way around"
        )
    )
    unit: Literal["cm", "in", "mixed", "unknown"] = Field(description="Unit of the chart overall")
    rows: list[ChartRow] = Field(default_factory=list)
    fabric_composition: str | None = Field(
        default=None, description="e.g. '100% cotton', '95% cotton 5% elastane'"
    )
    knit_or_woven: Literal["knit", "woven", "unknown"] = "unknown"
    cut: Cut | None = Field(default=None, description="set_in, raglan or drop_shoulder if stated")
    length_from: Literal["hps", "center_back", "unknown"] = Field(
        default="unknown",
        description="Where the body length is measured from: high point of shoulder or centre back",
    )
    sleeve_from: Literal["shoulder_seam", "center_back", "unknown"] = Field(
        default="unknown",
        description="Where sleeve length is measured from",
    )
    notes: str | None = Field(default=None, description="Anything ambiguous, one sentence")
    confidence: Confidence = Field(description="How sure you are the extraction is correct")


class ChartStatus(StrEnum):
    OK = "ok"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"
    NOT_FOUND = "not_found"


class ChartClassification(BaseModel):
    model_config = ConfigDict(frozen=True)

    chart_kind: Literal["body", "garment", "unknown"]
    measure_basis: Literal["flat", "circumference", "mixed", "unknown"]
    unit: Literal["cm", "in", "mixed", "unknown"]


class NormalisedChart(BaseModel):
    """What the pipeline stores: one garment per size, in cm, with provenance."""

    model_config = ConfigDict(frozen=True)

    status: ChartStatus
    classification: ChartClassification
    stretch: StretchClass | None = None
    fabric_composition: str | None = None
    sizes: list[GarmentModel] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    model_id: str | None = None
    #: Measure names on the page that could not be mapped to a garment field.
    unmapped_measures: list[str] = Field(default_factory=list)
