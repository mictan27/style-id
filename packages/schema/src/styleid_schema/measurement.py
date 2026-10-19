from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from styleid_fit.types import Confidence, Measurement, Source


class MeasurementModel(BaseModel):
    """One number in cm with where it came from and how much to trust it."""

    model_config = ConfigDict(frozen=True)

    value_cm: float = Field(gt=0, lt=400)
    source: Source
    confidence: Confidence = Confidence.MEDIUM

    def to_engine(self) -> Measurement:
        return Measurement(self.value_cm, self.source, self.confidence)

    @classmethod
    def from_engine(cls, m: Measurement) -> MeasurementModel:
        return cls(value_cm=m.value_cm, source=m.source, confidence=m.confidence)
