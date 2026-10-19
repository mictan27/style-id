from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from styleid_fit.types import Body, BodyField, Landmarks, Source

from .measurement import MeasurementModel


class LandmarksModel(BaseModel):
    """Vertical positions in cm below the high point of shoulder."""

    model_config = ConfigDict(frozen=True)

    waist_line_cm: float = Field(gt=0, lt=150)
    hip_line_cm: float = Field(gt=0, lt=150)
    wrist_cm: float = Field(gt=0, lt=150)

    def to_engine(self) -> Landmarks:
        return Landmarks(self.waist_line_cm, self.hip_line_cm, self.wrist_cm)

    @classmethod
    def from_engine(cls, lm: Landmarks) -> LandmarksModel:
        return cls(waist_line_cm=lm.waist_line_cm, hip_line_cm=lm.hip_line_cm, wrist_cm=lm.wrist_cm)


class BodyModel(BaseModel):
    """The body record: nine tape-equivalent measurements plus optional landmarks.

    The MHR mesh itself is stored as a blob and referenced by the API, not carried here.
    """

    model_config = ConfigDict(frozen=True)

    source: Source
    measurements: dict[BodyField, MeasurementModel] = Field(default_factory=dict)
    landmarks: LandmarksModel | None = None

    def to_engine(self) -> Body:
        return Body(
            measurements={k: v.to_engine() for k, v in self.measurements.items()},
            landmarks=self.landmarks.to_engine() if self.landmarks else None,
        )

    @classmethod
    def from_engine(cls, b: Body, source: Source) -> BodyModel:
        return cls(
            source=source,
            measurements={k: MeasurementModel.from_engine(v) for k, v in b.measurements.items()},
            landmarks=LandmarksModel.from_engine(b.landmarks) if b.landmarks else None,
        )
