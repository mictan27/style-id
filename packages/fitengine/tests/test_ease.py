from conftest import garment

from styleid_fit import (
    BodyField,
    Cut,
    GarmentField,
    Zone,
    body_ease,
    garment_extent,
    reference_delta,
)
from styleid_fit.ease import shoulder_overhang_per_side
from styleid_fit.thresholds import HPS_TO_CENTER_BACK_DROP_CM


def test_flat_widths_double_to_circumference(grey_tee):
    assert garment_extent(grey_tee, Zone.CHEST) == 100
    assert garment_extent(grey_tee, Zone.HEM) == 98
    assert garment_extent(grey_tee, Zone.BICEP) == 36


def test_shoulder_and_lengths_are_not_doubled(grey_tee):
    assert garment_extent(grey_tee, Zone.SHOULDER) == 44
    assert garment_extent(grey_tee, Zone.LENGTH) == 70
    assert garment_extent(grey_tee, Zone.SLEEVE) == 20


def test_missing_field_gives_none(grey_tee):
    assert garment_extent(grey_tee, Zone.WAIST) is None
    assert garment_extent(grey_tee, Zone.COLLAR) is None


def test_center_back_length_is_normalised_to_hps():
    g = garment(length=68)
    g_cb = garment(length=68)
    g_cb = type(g_cb)(**{**g_cb.__dict__, "length_from_center_back": True})
    assert garment_extent(g_cb, Zone.LENGTH) == 68 + HPS_TO_CENTER_BACK_DROP_CM
    assert garment_extent(g, Zone.LENGTH) == 68


def test_center_back_sleeve_subtracts_half_shoulder():
    g = garment(cut=Cut.RAGLAN, sleeve_length=80, shoulder_width=44)
    g = type(g)(**{**g.__dict__, "sleeve_from_center_back": True})
    assert garment_extent(g, Zone.SLEEVE) == 80 - 22


def test_center_back_sleeve_without_shoulder_is_unknown():
    g = garment(cut=Cut.RAGLAN, sleeve_length=80)
    g = type(g)(**{**g.__dict__, "sleeve_from_center_back": True})
    assert garment_extent(g, Zone.SLEEVE) is None


def test_body_ease_per_zone(grey_tee, avg_body):
    e = body_ease(grey_tee, avg_body)
    assert e[Zone.CHEST] == 4  # 100 - 96
    assert e[Zone.SHOULDER] == 0
    assert e[Zone.HEM] == 0  # 98 - 98
    assert e[Zone.BICEP] == 5  # 36 - 31
    assert Zone.WAIST not in e  # tee has no waist width
    assert Zone.LENGTH not in e  # positions are not ease


def test_reference_delta_includes_lengths(grey_tee):
    new = garment(chest_width=52, length=72, sleeve_length=20, shoulder_width=46)
    d = reference_delta(new, grey_tee)
    assert d[Zone.CHEST] == 4  # (52-50)*2
    assert d[Zone.LENGTH] == 2
    assert d[Zone.SLEEVE] == 0
    assert d[Zone.SHOULDER] == 2
    assert Zone.HEM not in d


def test_shoulder_overhang_is_per_side(avg_body):
    assert shoulder_overhang_per_side(garment(shoulder_width=48), avg_body) == 2
    assert shoulder_overhang_per_side(garment(shoulder_width=40), avg_body) == -2
    assert shoulder_overhang_per_side(garment(chest_width=50), avg_body) is None


def test_every_zone_maps_to_known_fields():
    from styleid_fit import ZONE_SPECS

    for spec in ZONE_SPECS.values():
        assert isinstance(spec.garment_field, GarmentField)
        assert isinstance(spec.body_field, BodyField)
