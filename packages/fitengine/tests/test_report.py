from conftest import garment
from test_sizepick import tee_run

from styleid_fit import (
    Basis,
    Confidence,
    Direction,
    Label,
    Outcome,
    Preferences,
    Source,
    StretchClass,
    Zone,
    build_report,
    nudge,
)


def test_report_with_reference_and_body(grey_tee, avg_body):
    r = build_report(tee_run(), avg_body, [grey_tee])
    assert r.pick is not None and r.pick.size_label == "M"
    assert r.runner_up is not None
    assert r.reference_size_label == "M"
    chest = r.pick.zone(Zone.CHEST)
    assert chest is not None
    assert chest.basis is Basis.REFERENCE
    assert chest.delta_vs_ref_cm == 0
    assert chest.ease_cm == 4
    assert chest.label is Label.REGULAR  # anchored on the grey tee's tag, not the 4 cm body ease
    length = r.pick.zone(Zone.LENGTH)
    assert length is not None and length.position is not None
    assert length.position.text == "hem lands 4 cm below your hip line"  # M length 68, hip line 64
    assert length.label is None


def test_report_body_only_uses_body_labels(avg_body):
    r = build_report(tee_run(), avg_body, [])
    assert r.reference_size_label is None
    chest = r.pick.zone(Zone.CHEST)
    assert chest.basis is Basis.BODY
    assert chest.label is Label.REGULAR  # L: 104 - 96 = 8 -> regular for cotton jersey


def test_report_reference_only_has_no_ease_or_positions(grey_tee):
    r = build_report(tee_run(), None, [grey_tee])
    chest = r.pick.zone(Zone.CHEST)
    assert chest.ease_cm is None and chest.delta_vs_ref_cm == 0
    assert r.pick.zone(Zone.LENGTH).position is None
    assert r.pick.zone(Zone.LENGTH).delta_vs_ref_cm == -2  # M in this run is 68 vs grey tee 70


def test_diffs_describe_runner_up_minus_pick(grey_tee):
    r = build_report(tee_run(), None, [grey_tee])
    assert r.pick.size_label == "M" and r.runner_up.size_label == "S"
    assert r.diffs_cm[Zone.CHEST] == -4  # (48 - 50) * 2: the runner-up is 4 cm smaller around
    assert r.diffs_cm[Zone.LENGTH] == -2
    assert Zone.WAIST not in r.diffs_cm  # neither size has a waist width


def test_excluded_sizes_are_still_reported(avg_body):
    r = build_report(tee_run(stretch=StretchClass.RIGID_WOVEN), avg_body, [])
    s = next(x for x in r.sizes if x.size_label == "S")
    assert s.excluded_reason is not None and s.score is None
    assert r.pick.size_label != "S"


def test_low_confidence_propagates():
    run = [
        garment(
            size_label="M", chest_width=50, source=Source.BRAND_EASE_ESTIMATE, conf=Confidence.LOW
        )
    ]
    ref = garment(size_label="M", chest_width=50)
    r = build_report(run, None, [ref])
    assert r.overall_confidence is Confidence.LOW


def test_empty_report():
    r = build_report([], None, [])
    assert r.pick is None and r.sizes == ()


def test_nudge_moves_toward_the_fix():
    p = Preferences()
    p = nudge(p, Outcome(kept=False, zone=Zone.CHEST, direction=Direction.TIGHT))
    assert p.shift(Zone.CHEST) == 1.0
    p = nudge(p, Outcome(kept=False, zone=Zone.CHEST, direction=Direction.LOOSE), step=0.5)
    assert p.shift(Zone.CHEST) == 0.5
    assert nudge(p, Outcome(kept=True)) == p
    assert nudge(p, Outcome(kept=False)) == p


def test_nudge_changes_the_pick(grey_tee):
    run = tee_run()
    assert build_report(run, None, [grey_tee]).pick.size_label == "M"
    prefs = Preferences()
    for _ in range(6):  # 1 cm per return; a size grade is 4 cm around
        prefs = nudge(prefs, Outcome(kept=False, zone=Zone.CHEST, direction=Direction.TIGHT))
    assert build_report(run, None, [grey_tee], prefs).pick.size_label == "L"
