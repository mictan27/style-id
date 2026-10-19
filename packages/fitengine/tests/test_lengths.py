from conftest import body, garment

from styleid_fit import Landmarks, hem_position, landmarks_for, sleeve_position
from styleid_fit.thresholds import DEFAULT_WAIST_TO_HIP_CM


def test_landmarks_derived_from_measurements(avg_body):
    lm = landmarks_for(avg_body)
    assert lm is not None
    assert lm.waist_line_cm == 46
    assert lm.hip_line_cm == 46 + DEFAULT_WAIST_TO_HIP_CM
    assert lm.wrist_cm == 62


def test_explicit_landmarks_win():
    b = body(back_length=46, arm_length=62, landmarks=Landmarks(45, 66, 61))
    assert landmarks_for(b) == Landmarks(45, 66, 61)


def test_landmarks_need_back_and_arm():
    assert landmarks_for(body(chest=96)) is None


def test_hem_below_waist(avg_body):
    p = hem_position(garment(length=51), avg_body)
    assert p is not None
    assert p.landmark == "waist line"
    assert p.offset_cm == 5
    assert p.text == "hem lands 5 cm below your waist line"


def test_hem_above_hip_when_closer_to_hip(avg_body):
    # hip line at 64; 61 is 3 above the hip and 15 below the waist -> hip is nearer
    p = hem_position(garment(length=61), avg_body)
    assert p is not None
    assert p.text == "hem lands 3 cm above your hip line"


def test_hem_right_at_landmark(avg_body):
    p = hem_position(garment(length=46.2), avg_body)
    assert p is not None
    assert p.text == "hem lands right at your waist line"


def test_hem_fractional_offsets_show_one_decimal(avg_body):
    p = hem_position(garment(length=48.5), avg_body)
    assert p is not None
    assert p.text == "hem lands 2.5 cm below your waist line"


def test_hem_requires_body_landmarks():
    assert hem_position(garment(length=70), body(chest=96)) is None
    assert hem_position(garment(chest_width=50), body(back_length=46, arm_length=62)) is None


def test_long_sleeve_vs_wrist(avg_body):
    assert (
        sleeve_position(garment(sleeve_length=64), avg_body).text
        == "sleeve ends 2 cm past your wrist"
    )
    assert (
        sleeve_position(garment(sleeve_length=59), avg_body).text
        == "sleeve ends 3 cm short of your wrist"
    )
    assert (
        sleeve_position(garment(sleeve_length=62), avg_body).text
        == "sleeve ends right at your wrist"
    )


def test_short_sleeve_has_no_wrist_position(avg_body):
    assert sleeve_position(garment(sleeve_length=20), avg_body) is None
