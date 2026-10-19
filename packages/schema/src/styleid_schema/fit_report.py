from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from styleid_fit.types import (
    Basis,
    Confidence,
    Direction,
    FitReport,
    Label,
    Outcome,
    Position,
    Preferences,
    SizeResult,
    Zone,
    ZoneResult,
)


class PositionModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    landmark: str
    offset_cm: float
    text: str

    @classmethod
    def from_engine(cls, p: Position) -> PositionModel:
        return cls(landmark=p.landmark, offset_cm=p.offset_cm, text=p.text)


class ZoneResultModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    zone: Zone
    label: Label | None
    basis: Basis | None
    ease_cm: float | None = None
    delta_vs_ref_cm: float | None = None
    position: PositionModel | None = None
    confidence: Confidence

    @classmethod
    def from_engine(cls, z: ZoneResult) -> ZoneResultModel:
        return cls(
            zone=z.zone,
            label=z.label,
            basis=z.basis,
            ease_cm=z.ease_cm,
            delta_vs_ref_cm=z.delta_vs_ref_cm,
            position=PositionModel.from_engine(z.position) if z.position else None,
            confidence=z.confidence,
        )


class SizeResultModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    size_label: str
    zones: list[ZoneResultModel]
    score: float | None
    excluded_reason: str | None = None

    @classmethod
    def from_engine(cls, s: SizeResult) -> SizeResultModel:
        return cls(
            size_label=s.size_label,
            zones=[ZoneResultModel.from_engine(z) for z in s.zones],
            score=s.score,
            excluded_reason=s.excluded_reason,
        )


class FitReportModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    engine_version: str
    pick: SizeResultModel | None
    runner_up: SizeResultModel | None
    sizes: list[SizeResultModel]
    diffs_cm: dict[Zone, float] = Field(default_factory=dict)
    reference_size_label: str | None = None
    overall_confidence: Confidence

    @classmethod
    def from_engine(cls, r: FitReport) -> FitReportModel:
        return cls(
            engine_version=r.engine_version,
            pick=SizeResultModel.from_engine(r.pick) if r.pick else None,
            runner_up=SizeResultModel.from_engine(r.runner_up) if r.runner_up else None,
            sizes=[SizeResultModel.from_engine(s) for s in r.sizes],
            diffs_cm=dict(r.diffs_cm),
            reference_size_label=r.reference_size_label,
            overall_confidence=r.overall_confidence,
        )


class PreferencesModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    shift_cm: dict[Zone, float] = Field(default_factory=dict)

    def to_engine(self) -> Preferences:
        return Preferences(shift_cm=dict(self.shift_cm))

    @classmethod
    def from_engine(cls, p: Preferences) -> PreferencesModel:
        return cls(shift_cm=dict(p.shift_cm))


class OutcomeModel(BaseModel):
    """The one post-delivery question: kept or returned, and if returned, which zone and how."""

    model_config = ConfigDict(frozen=True)

    kept: bool
    zone: Zone | None = None
    direction: Direction | None = None

    def to_engine(self) -> Outcome:
        return Outcome(kept=self.kept, zone=self.zone, direction=self.direction)
