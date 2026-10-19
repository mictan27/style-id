from conftest import garment
from hypothesis import given
from hypothesis import strategies as st

from styleid_fit import Basis, Cut, Preferences, StretchClass, Zone, exclude, pick, targets
from styleid_fit.thresholds import population_default_ease


def tee_run(stretch=StretchClass.COTTON_JERSEY, cut=Cut.SET_IN):
    """A product's size run: S, M, L, XL, each 2 cm wider at the chest (flat)."""
    sizes = {"S": 48, "M": 50, "L": 52, "XL": 54}
    return [
        garment(
            size_label=s,
            stretch=stretch,
            cut=cut,
            chest_width=w,
            shoulder_width=w - 6,
            hem_width=w,
            bicep_width=w / 2 - 7,
            length=66 + 2 * i,
            sleeve_length=19 + i,
        )
        for i, (s, w) in enumerate(sizes.items())
    ]


def test_reference_target_wins_over_body(grey_tee, avg_body):
    t = targets(StretchClass.COTTON_JERSEY, avg_body, [grey_tee], Preferences())
    assert t[Zone.CHEST].basis is Basis.REFERENCE
    assert t[Zone.CHEST].garment_cm == 100
    assert t[Zone.LENGTH].basis is Basis.REFERENCE
    # The tee has no waist width, so waist falls back to the body plus the population default.
    assert t[Zone.WAIST].basis is Basis.BODY
    assert t[Zone.WAIST].garment_cm == 84 + population_default_ease(
        Zone.WAIST, StretchClass.COTTON_JERSEY
    )


def test_body_only_targets_have_no_positions(avg_body):
    t = targets(StretchClass.COTTON_JERSEY, avg_body, [], Preferences())
    assert Zone.LENGTH not in t
    assert Zone.SLEEVE not in t
    assert t[Zone.CHEST].garment_cm == 96 + population_default_ease(
        Zone.CHEST, StretchClass.COTTON_JERSEY
    )


def test_shift_moves_target(grey_tee, avg_body):
    t = targets(StretchClass.COTTON_JERSEY, avg_body, [grey_tee], Preferences({Zone.CHEST: 2.0}))
    assert t[Zone.CHEST].garment_cm == 102


def test_cross_stretch_reference_is_adjusted(grey_tee):
    # Shopping for a rigid shirt with only a jersey tee as reference: the target chest grows by
    # the difference between the two population defaults.
    t = targets(StretchClass.RIGID_WOVEN, None, [grey_tee], Preferences())
    expected = 100 + (
        population_default_ease(Zone.CHEST, StretchClass.RIGID_WOVEN)
        - population_default_ease(Zone.CHEST, StretchClass.COTTON_JERSEY)
    )
    assert t[Zone.CHEST].garment_cm == expected
    # Lengths are not adjusted for stretch.
    assert t[Zone.LENGTH].garment_cm == 70


def test_pick_matches_reference_without_a_body(grey_tee):
    p = pick(tee_run(), None, [grey_tee])
    assert p.best is not None and p.best.size_label == "M"
    assert p.runner_up is not None and p.runner_up.size_label in {"S", "L"}
    assert p.excluded == {}


def test_pick_with_body_only_lands_on_population_default(avg_body):
    # chest 96 + default regular ease 10 -> target 106: L (104) and XL (108) tie at the chest,
    # shoulder and bicep pull toward L
    p = pick(tee_run(), avg_body, [])
    assert p.best is not None and p.best.size_label == "L"


def test_hard_rule_excludes_too_tight_rigid_chest(avg_body):
    run = tee_run(stretch=StretchClass.RIGID_WOVEN)
    p = pick(run, avg_body, [])
    # S: chest 96 vs body 96 -> ease 0 < 2 minimum for rigid woven
    assert "S" in p.excluded
    assert "below the 2 cm minimum" in p.excluded["S"]
    assert all(r.size_label != "S" for r in p.ranked)


def test_set_in_shoulder_overhang_excludes(avg_body):
    too_wide = garment(size_label="XXL", shoulder_width=49, chest_width=58)
    assert exclude(too_wide, avg_body) == "shoulder seam sits 2.5 cm outside your shoulder point"
    too_narrow = garment(size_label="XS", shoulder_width=39, chest_width=50)
    assert exclude(too_narrow, avg_body) == "shoulder seam sits 2.5 cm inside your shoulder point"


def test_drop_shoulder_skips_the_shoulder_rule(avg_body):
    g = garment(size_label="L", cut=Cut.DROP_SHOULDER, shoulder_width=56, chest_width=58)
    assert exclude(g, avg_body) is None


def test_no_body_means_no_exclusions():
    assert exclude(garment(size_label="S", chest_width=30), None) is None


def test_empty_candidates():
    p = pick([], None, [])
    assert p.best is None and p.runner_up is None


@given(st.permutations(["S", "M", "L", "XL"]))
def test_pick_is_invariant_to_candidate_order(order):
    ref = garment(size_label="M", chest_width=50, shoulder_width=44, length=70)
    by_label = {c.size_label: c for c in tee_run()}
    p = pick([by_label[s] for s in order], None, [ref])
    assert [r.size_label for r in p.ranked] == ["M", "L", "S", "XL"]
