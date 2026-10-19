"""Tunable constants. Plain dicts so product can adjust them in the beta.

Every number here is an initial value from the proposal or a sensible guess
marked for tuning. Thresholds are the lower bounds of the FITTED, REGULAR and
RELAXED bands in cm of ease; anything below the first bound is TIGHT.
"""

from __future__ import annotations

from collections.abc import Mapping

from .types import StretchClass, Zone

Bands = tuple[float, float, float]  # (fitted_min, regular_min, relaxed_min)

_CHEST_LIKE: Mapping[StretchClass, Bands] = {
    StretchClass.RIGID_WOVEN: (4.0, 10.0, 18.0),  # from the proposal
    StretchClass.WOVEN_ELASTANE: (2.0, 8.0, 16.0),
    StretchClass.COTTON_JERSEY: (0.0, 6.0, 14.0),  # from the proposal
    StretchClass.JERSEY_ELASTANE: (-4.0, 2.0, 10.0),
}

_BICEP: Mapping[StretchClass, Bands] = {
    StretchClass.RIGID_WOVEN: (2.0, 5.0, 9.0),
    StretchClass.WOVEN_ELASTANE: (1.0, 4.0, 8.0),
    StretchClass.COTTON_JERSEY: (0.0, 3.0, 7.0),
    StretchClass.JERSEY_ELASTANE: (-2.0, 1.0, 5.0),
}

# Shoulder is a width difference (garment seam-to-seam minus body shoulder width).
_SHOULDER: Mapping[StretchClass, Bands] = {
    StretchClass.RIGID_WOVEN: (-1.0, 1.0, 3.0),
    StretchClass.WOVEN_ELASTANE: (-1.0, 1.0, 3.0),
    StretchClass.COTTON_JERSEY: (-2.0, 1.0, 3.0),
    StretchClass.JERSEY_ELASTANE: (-2.0, 1.0, 3.0),
}

# Collar is a circumference compared with neck circumference (shirts only).
_COLLAR: Mapping[StretchClass, Bands] = {
    StretchClass.RIGID_WOVEN: (1.0, 2.0, 4.0),
    StretchClass.WOVEN_ELASTANE: (0.5, 2.0, 4.0),
    StretchClass.COTTON_JERSEY: (0.0, 1.5, 4.0),
    StretchClass.JERSEY_ELASTANE: (-1.0, 1.0, 4.0),
}

THRESHOLDS: Mapping[Zone, Mapping[StretchClass, Bands]] = {
    Zone.CHEST: _CHEST_LIKE,
    Zone.WAIST: _CHEST_LIKE,
    Zone.HEM: _CHEST_LIKE,
    Zone.BICEP: _BICEP,
    Zone.SHOULDER: _SHOULDER,
    Zone.COLLAR: _COLLAR,
}

#: Chest ease below this is physically too small for the fabric; the size is removed.
HARD_MIN_CHEST_EASE: Mapping[StretchClass, float] = {
    StretchClass.RIGID_WOVEN: 2.0,
    StretchClass.WOVEN_ELASTANE: 0.0,
    StretchClass.COTTON_JERSEY: -2.0,
    StretchClass.JERSEY_ELASTANE: -8.0,
}

#: A set-in shoulder seam more than this far off the shoulder point (per side) excludes a size.
SHOULDER_MAX_OVERHANG_CM = 2.0

#: Weights for the size-pick score. Chest and shoulder matter most.
ZONE_WEIGHTS: Mapping[Zone, float] = {
    Zone.CHEST: 3.0,
    Zone.SHOULDER: 3.0,
    Zone.WAIST: 1.0,
    Zone.HEM: 1.0,
    Zone.BICEP: 1.5,
    Zone.COLLAR: 2.0,
    Zone.LENGTH: 1.5,
    Zone.SLEEVE: 1.0,
}


#: Preferred ease when the user has no reference garment: middle of the REGULAR band.
def population_default_ease(zone: Zone, stretch: StretchClass) -> float:
    _fitted_min, regular_min, relaxed_min = THRESHOLDS[zone][stretch]
    return (regular_min + relaxed_min) / 2.0


#: Step applied to a zone's shift when a return names it.
NUDGE_STEP_CM = 1.0

#: HPS-to-hem length is longer than centre-back length by roughly the shoulder slope.
HPS_TO_CENTER_BACK_DROP_CM = 2.5

#: Default distance from waist line to hip line when the body record has no landmarks.
DEFAULT_WAIST_TO_HIP_CM = 18.0

#: Sleeves shorter than this are short sleeves; wrist position is not reported for them.
SHORT_SLEEVE_MAX_CM = 35.0

#: Below this body/garment confidence mix, the report is low confidence.
ENGINE_VERSION = "0.1.0"
