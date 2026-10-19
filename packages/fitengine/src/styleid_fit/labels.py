"""Zone labels from ease and stretch class, with reference-anchored labelling."""

from __future__ import annotations

from .thresholds import THRESHOLDS
from .types import Label, StretchClass, Zone

_ORDER = (Label.TIGHT, Label.FITTED, Label.REGULAR, Label.RELAXED)


def label_zone(ease_cm: float, zone: Zone, stretch: StretchClass) -> Label:
    fitted_min, regular_min, relaxed_min = THRESHOLDS[zone][stretch]
    if ease_cm < fitted_min:
        return Label.TIGHT
    if ease_cm < regular_min:
        return Label.FITTED
    if ease_cm < relaxed_min:
        return Label.REGULAR
    return Label.RELAXED


def band_midpoint(label: Label, zone: Zone, stretch: StretchClass) -> float:
    """A representative ease for a label, used to anchor a reference garment.

    Open-ended bands (TIGHT, RELAXED) use the neighbouring band's width.
    """
    fitted_min, regular_min, relaxed_min = THRESHOLDS[zone][stretch]
    fitted_w = regular_min - fitted_min
    regular_w = relaxed_min - regular_min
    if label is Label.TIGHT:
        return fitted_min - fitted_w / 2.0
    if label is Label.FITTED:
        return fitted_min + fitted_w / 2.0
    if label is Label.REGULAR:
        return regular_min + regular_w / 2.0
    return relaxed_min + regular_w / 2.0


def label_from_reference(
    delta_cm: float,
    ref_label: Label,
    zone: Zone,
    stretch: StretchClass,
) -> Label:
    """Label a new garment from how much wider it is than a reference the user has tagged.

    The reference is anchored at the middle of its tagged band for the *new*
    garment's stretch class, then shifted by the delta. This skips body error
    entirely, which is the point of the reference-garment wedge.
    """
    return label_zone(band_midpoint(ref_label, zone, stretch) + delta_cm, zone, stretch)


def label_index(label: Label) -> int:
    return _ORDER.index(label)
