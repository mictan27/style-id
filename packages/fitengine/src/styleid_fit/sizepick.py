"""Size pick: weighted distance from the user's preferred garment, after hard rules."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from statistics import fmean

from .ease import body_ease, body_extent, garment_extent, shoulder_overhang_per_side
from .thresholds import (
    HARD_MIN_CHEST_EASE,
    SHOULDER_MAX_OVERHANG_CM,
    ZONE_WEIGHTS,
    population_default_ease,
)
from .types import (
    EASE_ZONES,
    ZONE_SPECS,
    Basis,
    Body,
    Cut,
    Garment,
    Preferences,
    StretchClass,
    Zone,
)


@dataclass(frozen=True)
class Target:
    zone: Zone
    garment_cm: float
    basis: Basis


def select_references(refs: Sequence[Garment], stretch: StretchClass) -> tuple[Garment, ...]:
    """References of the same stretch class win; otherwise fall back to all of them."""
    same = tuple(r for r in refs if r.stretch is stretch)
    return same if same else tuple(refs)


def _ref_target(zone: Zone, refs: Sequence[Garment], stretch: StretchClass) -> float | None:
    values: list[float] = []
    for r in refs:
        g = garment_extent(r, zone)
        if g is None:
            continue
        if zone in EASE_ZONES and r.stretch is not stretch:
            # A "regular" jersey tee and a "regular" rigid shirt sit at different ease;
            # move the reference by the difference in population defaults.
            g += population_default_ease(zone, stretch) - population_default_ease(zone, r.stretch)
        values.append(g)
    return fmean(values) if values else None


def targets(
    stretch: StretchClass,
    body: Body | None,
    refs: Sequence[Garment],
    prefs: Preferences,
) -> dict[Zone, Target]:
    """Target garment extent per zone, in body-comparable cm.

    Reference garments win where they cover the zone. Otherwise the body plus
    the population default ease is used. Position zones need a reference.
    """
    chosen = select_references(refs, stretch)
    out: dict[Zone, Target] = {}
    for zone in ZONE_SPECS:
        t = _ref_target(zone, chosen, stretch)
        if t is not None:
            out[zone] = Target(zone, t + prefs.shift(zone), Basis.REFERENCE)
            continue
        if body is not None and zone in EASE_ZONES:
            b = body_extent(body, zone)
            if b is not None:
                default = population_default_ease(zone, stretch)
                out[zone] = Target(zone, b + default + prefs.shift(zone), Basis.BODY)
    return out


def score(garment: Garment, zone_targets: dict[Zone, Target]) -> float | None:
    """L(s) = Σ_z w_z (G_z - target_z)^2 over zones both sides cover. None if nothing overlaps."""
    total = 0.0
    n = 0
    for zone, t in zone_targets.items():
        g = garment_extent(garment, zone)
        if g is None:
            continue
        total += ZONE_WEIGHTS.get(zone, 1.0) * (g - t.garment_cm) ** 2
        n += 1
    return total if n else None


def exclude(garment: Garment, body: Body | None) -> str | None:
    """Hard rules that remove a size before scoring. Only apply when a body is known."""
    if body is None:
        return None
    ease = body_ease(garment, body)
    chest = ease.get(Zone.CHEST)
    if chest is not None:
        minimum = HARD_MIN_CHEST_EASE[garment.stretch]
        if chest < minimum:
            return (
                f"chest ease {chest:.1f} cm is below the {minimum:.0f} cm minimum "
                f"for {garment.stretch.value.replace('_', ' ')}"
            )
    if garment.cut is Cut.SET_IN:
        overhang = shoulder_overhang_per_side(garment, body)
        if overhang is not None and abs(overhang) > SHOULDER_MAX_OVERHANG_CM:
            where = "outside" if overhang > 0 else "inside"
            return f"shoulder seam sits {abs(overhang):.1f} cm {where} your shoulder point"
    return None


@dataclass(frozen=True)
class Ranked:
    size_label: str
    score: float


@dataclass(frozen=True)
class Pick:
    ranked: tuple[Ranked, ...]  # best first; excluded sizes are not here
    excluded: dict[str, str]
    targets: dict[Zone, Target]

    @property
    def best(self) -> Ranked | None:
        return self.ranked[0] if self.ranked else None

    @property
    def runner_up(self) -> Ranked | None:
        return self.ranked[1] if len(self.ranked) > 1 else None


def pick(
    candidates: Sequence[Garment],
    body: Body | None,
    refs: Sequence[Garment],
    prefs: Preferences | None = None,
) -> Pick:
    prefs = prefs or Preferences()
    if not candidates:
        return Pick((), {}, {})
    stretch = candidates[0].stretch
    zone_targets = targets(stretch, body, refs, prefs)
    ranked: list[Ranked] = []
    excluded: dict[str, str] = {}
    for g in candidates:
        label = g.size_label or "?"
        reason = exclude(g, body)
        if reason is not None:
            excluded[label] = reason
            continue
        s = score(g, zone_targets)
        if s is None:
            excluded[label] = "no measurements overlap with your body or references"
            continue
        ranked.append(Ranked(label, s))
    # Deterministic: by score, then by label so input order never changes the answer.
    ranked.sort(key=lambda r: (r.score, r.size_label))
    return Pick(tuple(ranked), excluded, zone_targets)
