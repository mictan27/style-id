from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from styleid_fit.types import Cut, Garment, GarmentField, GarmentKind, Label, StretchClass

from .measurement import MeasurementModel


class GarmentModel(BaseModel):
    """A garment as laid flat, in cm. Used for closet items and for each size of a product."""

    model_config = ConfigDict(frozen=True)

    kind: GarmentKind
    cut: Cut = Cut.SET_IN
    stretch: StretchClass
    size_label: str | None = None
    fit_tag: Label | None = Field(
        default=None, description="How the owner says it fits them. Closet references only."
    )
    length_from_center_back: bool = False
    sleeve_from_center_back: bool = False
    measurements: dict[GarmentField, MeasurementModel] = Field(default_factory=dict)

    def to_engine(self) -> Garment:
        return Garment(
            kind=self.kind,
            cut=self.cut,
            stretch=self.stretch,
            measurements={k: v.to_engine() for k, v in self.measurements.items()},
            size_label=self.size_label,
            fit_tag=self.fit_tag,
            length_from_center_back=self.length_from_center_back,
            sleeve_from_center_back=self.sleeve_from_center_back,
        )

    @classmethod
    def from_engine(cls, g: Garment) -> GarmentModel:
        return cls(
            kind=g.kind,
            cut=g.cut,
            stretch=g.stretch,
            size_label=g.size_label,
            fit_tag=g.fit_tag,
            length_from_center_back=g.length_from_center_back,
            sleeve_from_center_back=g.sleeve_from_center_back,
            measurements={k: MeasurementModel.from_engine(v) for k, v in g.measurements.items()},
        )
