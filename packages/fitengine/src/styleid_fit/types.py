"""Domain types for the fit engine.

Everything here is a frozen dataclass or an Enum so the engine stays pure and
every verdict is reproducible from its inputs. The enums are the single source
of truth for zone and measurement vocabulary; `styleid_schema` re-exports them.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum


class GarmentKind(StrEnum):
    TEE = "tee"
    SHIRT = "shirt"
    SWEATER = "sweater"
    HOODIE = "hoodie"


class Cut(StrEnum):
    SET_IN = "set_in"
    RAGLAN = "raglan"
    DROP_SHOULDER = "drop_shoulder"


class StretchClass(StrEnum):
    RIGID_WOVEN = "rigid_woven"
    WOVEN_ELASTANE = "woven_elastane"
    COTTON_JERSEY = "cotton_jersey"
    JERSEY_ELASTANE = "jersey_elastane"


class Source(StrEnum):
    """Where a measurement came from. Carried on every value."""

    FLATLAY = "flatlay"
    CHART = "chart"
    BRAND_EASE_ESTIMATE = "brand_ease_estimate"
    MANUAL = "manual"
    LIDAR = "lidar"
    PHOTO = "photo"
    SIZE_ANCHOR = "size_anchor"


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class GarmentField(StrEnum):
    """Garment measurements as laid flat, in cm, following the proposal's schema."""

    CHEST_WIDTH = "chest_width"
    WAIST_WIDTH = "waist_width"
    HEM_WIDTH = "hem_width"
    BICEP_WIDTH = "bicep_width"
    SHOULDER_WIDTH = "shoulder_width"
    SLEEVE_LENGTH = "sleeve_length"
    LENGTH = "length"
    COLLAR = "collar"


class BodyField(StrEnum):
    """The nine tape-equivalent body measurements, in cm."""

    HEIGHT = "height"
    NECK = "neck"
    SHOULDER = "shoulder"
    CHEST = "chest"
    WAIST = "waist"
    HIP = "hip"
    ARM_LENGTH = "arm_length"
    BICEP = "bicep"
    BACK_LENGTH = "back_length"


class Zone(StrEnum):
    """Fit zones reported to the user. Ease zones get a label; position zones get a position."""

    CHEST = "chest"
    SHOULDER = "shoulder"
    WAIST = "waist"
    HEM = "hem"
    BICEP = "bicep"
    COLLAR = "collar"
    LENGTH = "length"
    SLEEVE = "sleeve"


class ZoneKind(StrEnum):
    CIRCUMFERENCE = "circumference"  # garment flat width x2 vs body circumference
    WIDTH = "width"  # garment width vs body width (shoulder)
    DIRECT = "direct"  # garment value already a circumference (collar)
    POSITION = "position"  # garment length vs body landmark


class Label(StrEnum):
    TIGHT = "tight"
    FITTED = "fitted"
    REGULAR = "regular"
    RELAXED = "relaxed"


class Basis(StrEnum):
    REFERENCE = "reference"
    BODY = "body"


class Direction(StrEnum):
    TIGHT = "tight"
    LOOSE = "loose"


@dataclass(frozen=True)
class ZoneSpec:
    garment_field: GarmentField
    body_field: BodyField
    kind: ZoneKind


ZONE_SPECS: Mapping[Zone, ZoneSpec] = {
    Zone.CHEST: ZoneSpec(GarmentField.CHEST_WIDTH, BodyField.CHEST, ZoneKind.CIRCUMFERENCE),
    Zone.SHOULDER: ZoneSpec(GarmentField.SHOULDER_WIDTH, BodyField.SHOULDER, ZoneKind.WIDTH),
    Zone.WAIST: ZoneSpec(GarmentField.WAIST_WIDTH, BodyField.WAIST, ZoneKind.CIRCUMFERENCE),
    Zone.HEM: ZoneSpec(GarmentField.HEM_WIDTH, BodyField.HIP, ZoneKind.CIRCUMFERENCE),
    Zone.BICEP: ZoneSpec(GarmentField.BICEP_WIDTH, BodyField.BICEP, ZoneKind.CIRCUMFERENCE),
    Zone.COLLAR: ZoneSpec(GarmentField.COLLAR, BodyField.NECK, ZoneKind.DIRECT),
    Zone.LENGTH: ZoneSpec(GarmentField.LENGTH, BodyField.BACK_LENGTH, ZoneKind.POSITION),
    Zone.SLEEVE: ZoneSpec(GarmentField.SLEEVE_LENGTH, BodyField.ARM_LENGTH, ZoneKind.POSITION),
}

EASE_ZONES: tuple[Zone, ...] = tuple(
    z for z, s in ZONE_SPECS.items() if s.kind is not ZoneKind.POSITION
)
POSITION_ZONES: tuple[Zone, ...] = tuple(
    z for z, s in ZONE_SPECS.items() if s.kind is ZoneKind.POSITION
)


@dataclass(frozen=True)
class Measurement:
    value_cm: float
    source: Source
    confidence: Confidence = Confidence.MEDIUM


@dataclass(frozen=True)
class Garment:
    kind: GarmentKind
    cut: Cut
    stretch: StretchClass
    measurements: Mapping[GarmentField, Measurement] = field(default_factory=dict)
    size_label: str | None = None
    #: How the owner says this garment fits them. Only meaningful for closet references.
    fit_tag: Label | None = None
    #: Length measured from centre back neck instead of high point of shoulder.
    length_from_center_back: bool = False
    #: Sleeve measured from centre back neck (common for raglan and drop shoulder).
    sleeve_from_center_back: bool = False

    def value(self, f: GarmentField) -> float | None:
        m = self.measurements.get(f)
        return None if m is None else m.value_cm

    def has(self, f: GarmentField) -> bool:
        return f in self.measurements


@dataclass(frozen=True)
class Landmarks:
    """Vertical positions on the body, in cm below the high point of shoulder (HPS)."""

    waist_line_cm: float
    hip_line_cm: float
    wrist_cm: float


@dataclass(frozen=True)
class Body:
    measurements: Mapping[BodyField, Measurement] = field(default_factory=dict)
    landmarks: Landmarks | None = None

    def value(self, f: BodyField) -> float | None:
        m = self.measurements.get(f)
        return None if m is None else m.value_cm

    def has(self, f: BodyField) -> bool:
        return f in self.measurements


@dataclass(frozen=True)
class Position:
    """Where a garment edge lands relative to a body landmark."""

    landmark: str  # "waist line" | "hip line" | "wrist"
    offset_cm: float  # positive = below / past the landmark
    text: str


@dataclass(frozen=True)
class ZoneResult:
    zone: Zone
    label: Label | None
    basis: Basis | None
    ease_cm: float | None = None  # garment minus body, when a body covers the zone
    delta_vs_ref_cm: float | None = None  # garment minus reference, when a reference covers it
    position: Position | None = None
    confidence: Confidence = Confidence.MEDIUM


@dataclass(frozen=True)
class Preferences:
    """Learned per-user taste. `shift_cm` moves the target garment size per zone.

    Positive shift means the user wants more room than their references (or the
    population default) suggest. It starts at zero and is nudged by outcomes.
    """

    shift_cm: Mapping[Zone, float] = field(default_factory=dict)

    def shift(self, zone: Zone) -> float:
        return self.shift_cm.get(zone, 0.0)


@dataclass(frozen=True)
class Outcome:
    kept: bool
    zone: Zone | None = None
    direction: Direction | None = None


@dataclass(frozen=True)
class SizeResult:
    size_label: str
    zones: tuple[ZoneResult, ...]
    score: float | None  # None when excluded
    excluded_reason: str | None = None

    def zone(self, z: Zone) -> ZoneResult | None:
        for r in self.zones:
            if r.zone is z:
                return r
        return None


@dataclass(frozen=True)
class FitReport:
    engine_version: str
    pick: SizeResult | None
    runner_up: SizeResult | None
    sizes: tuple[SizeResult, ...]
    #: Per-zone difference (runner-up minus pick) in garment cm, for "what would change".
    diffs_cm: Mapping[Zone, float] = field(default_factory=dict)
    reference_size_label: str | None = None
    overall_confidence: Confidence = Confidence.MEDIUM
