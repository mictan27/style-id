"""Ease (garment minus body) and reference delta (garment minus reference)."""

from __future__ import annotations

from .thresholds import HPS_TO_CENTER_BACK_DROP_CM
from .types import (
    EASE_ZONES,
    ZONE_SPECS,
    Body,
    BodyField,
    Garment,
    GarmentField,
    Zone,
    ZoneKind,
)


def garment_extent(garment: Garment, zone: Zone) -> float | None:
    """The garment's value for a zone in body-comparable units.

    Flat widths are doubled to circumferences. Lengths are normalised to the
    HPS-to-hem convention and sleeves to shoulder-seam-to-cuff.
    """
    spec = ZONE_SPECS[zone]
    raw = garment.value(spec.garment_field)
    if raw is None:
        return None
    if spec.kind is ZoneKind.CIRCUMFERENCE:
        return raw * 2.0
    if zone is Zone.LENGTH and garment.length_from_center_back:
        return raw + HPS_TO_CENTER_BACK_DROP_CM
    if zone is Zone.SLEEVE and garment.sleeve_from_center_back:
        shoulder = garment.value(GarmentField.SHOULDER_WIDTH)
        if shoulder is None:
            return None
        return raw - shoulder / 2.0
    return raw


def body_extent(body: Body, zone: Zone) -> float | None:
    return body.value(ZONE_SPECS[zone].body_field)


def body_ease(garment: Garment, body: Body) -> dict[Zone, float]:
    """e_z = G_z - B_z for every ease zone both sides cover."""
    out: dict[Zone, float] = {}
    for zone in EASE_ZONES:
        g = garment_extent(garment, zone)
        b = body_extent(body, zone)
        if g is not None and b is not None:
            out[zone] = g - b
    return out


def reference_delta(new: Garment, ref: Garment) -> dict[Zone, float]:
    """Δ_z = G_new,z - G_ref,z for every zone both garments cover, lengths included."""
    out: dict[Zone, float] = {}
    for zone in ZONE_SPECS:
        g = garment_extent(new, zone)
        r = garment_extent(ref, zone)
        if g is not None and r is not None:
            out[zone] = g - r
    return out


def shoulder_overhang_per_side(garment: Garment, body: Body) -> float | None:
    """How far the shoulder seam sits off the shoulder point, per side. Positive = outside."""
    g = garment.value(GarmentField.SHOULDER_WIDTH)
    b = body.value(BodyField.SHOULDER)
    if g is None or b is None:
        return None
    return (g - b) / 2.0
