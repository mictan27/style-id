"""Lengths are reported as positions on the body, not as ease."""

from __future__ import annotations

from .ease import garment_extent
from .thresholds import DEFAULT_WAIST_TO_HIP_CM, SHORT_SLEEVE_MAX_CM
from .types import Body, BodyField, Garment, Landmarks, Position, Zone


def landmarks_for(body: Body) -> Landmarks | None:
    """Explicit landmarks when the body record has them, otherwise derived from measurements."""
    if body.landmarks is not None:
        return body.landmarks
    back = body.value(BodyField.BACK_LENGTH)
    arm = body.value(BodyField.ARM_LENGTH)
    if back is None or arm is None:
        return None
    return Landmarks(
        waist_line_cm=back,
        hip_line_cm=back + DEFAULT_WAIST_TO_HIP_CM,
        wrist_cm=arm,
    )


def _fmt(cm: float) -> str:
    rounded = round(cm)
    return f"{rounded:d} cm" if abs(cm - rounded) < 0.05 else f"{cm:.1f} cm"


def hem_position(garment: Garment, body: Body) -> Position | None:
    length = garment_extent(garment, Zone.LENGTH)
    lm = landmarks_for(body)
    if length is None or lm is None:
        return None
    candidates = (("waist line", lm.waist_line_cm), ("hip line", lm.hip_line_cm))
    landmark, at = min(candidates, key=lambda c: abs(length - c[1]))
    offset = length - at
    if abs(offset) < 0.5:
        text = f"hem lands right at your {landmark}"
    elif offset > 0:
        text = f"hem lands {_fmt(offset)} below your {landmark}"
    else:
        text = f"hem lands {_fmt(-offset)} above your {landmark}"
    return Position(landmark=landmark, offset_cm=offset, text=text)


def sleeve_position(garment: Garment, body: Body) -> Position | None:
    sleeve = garment_extent(garment, Zone.SLEEVE)
    lm = landmarks_for(body)
    if sleeve is None or lm is None or sleeve < SHORT_SLEEVE_MAX_CM:
        return None
    offset = sleeve - lm.wrist_cm
    if abs(offset) < 0.5:
        text = "sleeve ends right at your wrist"
    elif offset > 0:
        text = f"sleeve ends {_fmt(offset)} past your wrist"
    else:
        text = f"sleeve ends {_fmt(-offset)} short of your wrist"
    return Position(landmark="wrist", offset_cm=offset, text=text)
