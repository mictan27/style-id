import pytest
from hypothesis import given
from hypothesis import strategies as st

from styleid_fit import (
    THRESHOLDS,
    Label,
    StretchClass,
    Zone,
    band_midpoint,
    label_from_reference,
    label_zone,
)
from styleid_fit.labels import label_index

EASE_ZONES_WITH_THRESHOLDS = list(THRESHOLDS)


@pytest.mark.parametrize(
    ("ease", "stretch", "expected"),
    [
        (3.9, StretchClass.RIGID_WOVEN, Label.TIGHT),
        (4.0, StretchClass.RIGID_WOVEN, Label.FITTED),
        (9.9, StretchClass.RIGID_WOVEN, Label.FITTED),
        (10.0, StretchClass.RIGID_WOVEN, Label.REGULAR),
        (17.9, StretchClass.RIGID_WOVEN, Label.REGULAR),
        (18.0, StretchClass.RIGID_WOVEN, Label.RELAXED),
        (-0.1, StretchClass.COTTON_JERSEY, Label.TIGHT),
        (0.0, StretchClass.COTTON_JERSEY, Label.FITTED),
        (6.0, StretchClass.COTTON_JERSEY, Label.REGULAR),
        (14.0, StretchClass.COTTON_JERSEY, Label.RELAXED),
    ],
)
def test_chest_thresholds_from_proposal(ease, stretch, expected):
    assert label_zone(ease, Zone.CHEST, stretch) is expected


def test_stretch_tolerates_negative_ease():
    assert label_zone(-3, Zone.CHEST, StretchClass.JERSEY_ELASTANE) is Label.FITTED
    assert label_zone(-3, Zone.CHEST, StretchClass.RIGID_WOVEN) is Label.TIGHT


def test_band_midpoints_land_in_their_band():
    for zone in EASE_ZONES_WITH_THRESHOLDS:
        for stretch in StretchClass:
            for label in Label:
                assert label_zone(band_midpoint(label, zone, stretch), zone, stretch) is label


def test_reference_anchored_labels_follow_the_delta():
    # Grey tee is "regular" cotton jersey, anchored mid-band at 10 cm (band 6..14).
    # 3 cm more room keeps it regular; 4 cm reaches the relaxed boundary; 8 cm is clearly relaxed.
    jersey = StretchClass.COTTON_JERSEY
    assert label_from_reference(0, Label.REGULAR, Zone.CHEST, jersey) is Label.REGULAR
    assert label_from_reference(3, Label.REGULAR, Zone.CHEST, jersey) is Label.REGULAR
    assert label_from_reference(4, Label.REGULAR, Zone.CHEST, jersey) is Label.RELAXED
    assert label_from_reference(8, Label.REGULAR, Zone.CHEST, jersey) is Label.RELAXED
    assert label_from_reference(-4, Label.REGULAR, Zone.CHEST, jersey) is Label.REGULAR
    assert label_from_reference(-6, Label.REGULAR, Zone.CHEST, jersey) is Label.FITTED
    assert label_from_reference(-12, Label.REGULAR, Zone.CHEST, jersey) is Label.TIGHT
    # A reference tagged "fitted" anchors lower: the same garment reads one band tighter.
    assert label_from_reference(0, Label.FITTED, Zone.CHEST, jersey) is Label.FITTED
    assert label_from_reference(-4, Label.FITTED, Zone.CHEST, jersey) is Label.TIGHT


@given(
    zone=st.sampled_from(EASE_ZONES_WITH_THRESHOLDS),
    stretch=st.sampled_from(list(StretchClass)),
    a=st.floats(-30, 40),
    b=st.floats(-30, 40),
)
def test_labels_are_monotonic_in_ease(zone, stretch, a, b):
    lo, hi = sorted((a, b))
    assert label_index(label_zone(lo, zone, stretch)) <= label_index(label_zone(hi, zone, stretch))


@given(
    zone=st.sampled_from(EASE_ZONES_WITH_THRESHOLDS),
    stretch=st.sampled_from(list(StretchClass)),
    ref=st.sampled_from(list(Label)),
    a=st.floats(-30, 40),
    b=st.floats(-30, 40),
)
def test_reference_labels_are_monotonic_in_delta(zone, stretch, ref, a, b):
    lo, hi = sorted((a, b))
    assert label_index(label_from_reference(lo, ref, zone, stretch)) <= label_index(
        label_from_reference(hi, ref, zone, stretch)
    )


def test_thresholds_are_strictly_increasing():
    for zone, by_stretch in THRESHOLDS.items():
        for stretch, (f, r, x) in by_stretch.items():
            assert f < r < x, (zone, stretch)
