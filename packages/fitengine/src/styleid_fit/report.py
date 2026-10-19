"""Assemble a FitReport and learn from outcomes."""

from __future__ import annotations

from collections.abc import Sequence

from .ease import body_ease, garment_extent, reference_delta
from .labels import label_from_reference, label_zone
from .lengths import hem_position, sleeve_position
from .sizepick import Pick, pick, select_references
from .thresholds import ENGINE_VERSION, NUDGE_STEP_CM
from .types import (
    EASE_ZONES,
    ZONE_SPECS,
    Basis,
    Body,
    Confidence,
    Direction,
    FitReport,
    Garment,
    Label,
    Outcome,
    Preferences,
    SizeResult,
    Zone,
    ZoneResult,
)

_CONF_RANK = {Confidence.HIGH: 2, Confidence.MEDIUM: 1, Confidence.LOW: 0}


def _min_conf(*cs: Confidence | None) -> Confidence:
    present = [c for c in cs if c is not None]
    if not present:
        return Confidence.MEDIUM
    return min(present, key=lambda c: _CONF_RANK[c])


def primary_reference(new: Garment, refs: Sequence[Garment]) -> Garment | None:
    """The reference the report compares against: same stretch class if possible, then
    the one closest at the chest."""
    chosen = select_references(refs, new.stretch)
    if not chosen:
        return None

    def chest_gap(r: Garment) -> float:
        d = reference_delta(new, r).get(Zone.CHEST)
        return abs(d) if d is not None else float("inf")

    return min(chosen, key=chest_gap)


def zone_results(new: Garment, body: Body | None, ref: Garment | None) -> tuple[ZoneResult, ...]:
    ease = body_ease(new, body) if body is not None else {}
    delta = reference_delta(new, ref) if ref is not None else {}
    out: list[ZoneResult] = []
    for zone, spec in ZONE_SPECS.items():
        if garment_extent(new, zone) is None:
            continue
        g_conf = new.measurements[spec.garment_field].confidence
        e = ease.get(zone)
        d = delta.get(zone)
        label: Label | None = None
        basis: Basis | None = None
        other_conf: Confidence | None = None
        if zone in EASE_ZONES:
            if d is not None and ref is not None:
                label = label_from_reference(d, ref.fit_tag or Label.REGULAR, zone, new.stretch)
                basis = Basis.REFERENCE
                other_conf = ref.measurements[spec.garment_field].confidence
            elif e is not None and body is not None:
                label = label_zone(e, zone, new.stretch)
                basis = Basis.BODY
                other_conf = body.measurements[spec.body_field].confidence
            position = None
        else:
            position = None
            if body is not None:
                position = (
                    hem_position(new, body) if zone is Zone.LENGTH else sleeve_position(new, body)
                )
                if position is not None:
                    basis = Basis.BODY
                    other_conf = body.measurements[spec.body_field].confidence
            if d is not None and ref is not None:
                basis = Basis.REFERENCE if position is None else basis
                other_conf = _min_conf(other_conf, ref.measurements[spec.garment_field].confidence)
        if label is None and position is None and d is None:
            continue
        out.append(
            ZoneResult(
                zone=zone,
                label=label,
                basis=basis,
                ease_cm=e,
                delta_vs_ref_cm=d,
                position=position,
                confidence=_min_conf(g_conf, other_conf),
            )
        )
    return tuple(out)


def _size_result(g: Garment, body: Body | None, ref: Garment | None, p: Pick) -> SizeResult:
    label = g.size_label or "?"
    s = next((r.score for r in p.ranked if r.size_label == label), None)
    return SizeResult(
        size_label=label,
        zones=zone_results(g, body, ref),
        score=s,
        excluded_reason=p.excluded.get(label),
    )


def build_report(
    candidates: Sequence[Garment],
    body: Body | None,
    refs: Sequence[Garment] = (),
    prefs: Preferences | None = None,
) -> FitReport:
    prefs = prefs or Preferences()
    if not candidates:
        return FitReport(ENGINE_VERSION, None, None, ())
    ref = primary_reference(candidates[0], refs)
    p = pick(candidates, body, refs, prefs)
    by_label = {(g.size_label or "?"): g for g in candidates}
    sizes = tuple(_size_result(g, body, ref, p) for g in candidates)
    best = next((s for s in sizes if p.best and s.size_label == p.best.size_label), None)
    second = next(
        (s for s in sizes if p.runner_up and s.size_label == p.runner_up.size_label), None
    )
    diffs: dict[Zone, float] = {}
    if best is not None and second is not None:
        gb, gs = by_label[best.size_label], by_label[second.size_label]
        for zone in ZONE_SPECS:
            a, b = garment_extent(gb, zone), garment_extent(gs, zone)
            if a is not None and b is not None and abs(b - a) > 1e-9:
                diffs[zone] = b - a
    overall = _min_conf(*(z.confidence for z in best.zones)) if best else Confidence.LOW
    return FitReport(
        engine_version=ENGINE_VERSION,
        pick=best,
        runner_up=second,
        sizes=sizes,
        diffs_cm=diffs,
        reference_size_label=ref.size_label if ref else None,
        overall_confidence=overall,
    )


def nudge(prefs: Preferences, outcome: Outcome, step: float = NUDGE_STEP_CM) -> Preferences:
    """A return that names a zone moves that zone's target by one step toward the fix."""
    if outcome.kept or outcome.zone is None or outcome.direction is None:
        return prefs
    sign = 1.0 if outcome.direction is Direction.TIGHT else -1.0
    shifts = dict(prefs.shift_cm)
    shifts[outcome.zone] = shifts.get(outcome.zone, 0.0) + sign * step
    return Preferences(shift_cm=shifts)
