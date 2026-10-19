import math

import numpy as np
import pytest

from styleid_bodyfit.measure import (
    BodyLandmarks,
    Mesh,
    convex_hull_2d,
    fullest_slice_y,
    measure_body,
    narrowest_slice_y,
    path_length,
    perimeter,
    slice_perimeter,
)
from styleid_fit.types import BodyField


def cylinder(radius: float, height: float, *, segments: int = 64, cx: float = 0.0) -> Mesh:
    """A closed-side cylinder along Y from 0 to height, centred at x=cx, z=0."""
    ang = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    ring = np.stack([cx + radius * np.cos(ang), np.zeros(segments), radius * np.sin(ang)], axis=1)
    bottom = ring.copy()
    top = ring.copy()
    top[:, 1] = height
    verts = np.vstack([bottom, top])
    faces = []
    for i in range(segments):
        j = (i + 1) % segments
        faces.append([i, j, segments + i])
        faces.append([j, segments + j, segments + i])
    return Mesh(verts.astype(np.float64), np.asarray(faces, dtype=np.int64))


def hourglass(r_top: float, r_mid: float, r_bot: float, height: float, segments: int = 48) -> Mesh:
    """Three stacked rings: wide, narrow, wide."""
    ang = np.linspace(0, 2 * np.pi, segments, endpoint=False)

    def ring(r, y):
        return np.stack([r * np.cos(ang), np.full(segments, y), r * np.sin(ang)], axis=1)

    rings = [ring(r_bot, 0.0), ring(r_mid, height / 2), ring(r_top, height)]
    verts = np.vstack(rings)
    faces = []
    for level in range(2):
        base = level * segments
        for i in range(segments):
            j = (i + 1) % segments
            faces.append([base + i, base + j, base + segments + i])
            faces.append([base + j, base + segments + j, base + segments + i])
    return Mesh(verts.astype(np.float64), np.asarray(faces, dtype=np.int64))


def test_cylinder_slice_perimeter_is_circumference():
    r = 0.15
    m = cylinder(r, 1.0)
    p = slice_perimeter(m, 0.5)
    assert p == pytest.approx(2 * math.pi * r, rel=0.01)


def test_slice_outside_mesh_is_zero():
    assert slice_perimeter(cylinder(0.1, 1.0), 1.5) == 0.0


def test_convex_hull_bridges_hollows():
    # A square with an inward dent still measures as a square.
    square = np.array([[0, 0], [1, 0], [1, 1], [0, 1], [0.5, 0.2]], dtype=float)
    hull = convex_hull_2d(square)
    assert len(hull) == 4
    assert perimeter(hull) == pytest.approx(4.0)


def test_hull_degenerate_inputs():
    assert perimeter(convex_hull_2d(np.empty((0, 2)))) == 0.0
    assert perimeter(convex_hull_2d(np.array([[0.0, 0.0]]))) == 0.0
    two = convex_hull_2d(np.array([[0.0, 0.0], [1.0, 0.0]]))
    assert perimeter(two) == pytest.approx(2.0)  # out and back


def test_x_range_isolates_one_limb():
    torso = cylinder(0.15, 1.0)
    arm = cylinder(0.05, 1.0, cx=0.3)
    both = Mesh(
        np.vstack([torso.vertices, arm.vertices]),
        np.vstack([torso.faces, arm.faces + len(torso.vertices)]),
    )
    hull_all = slice_perimeter(both, 0.5)
    arm_only = slice_perimeter(both, 0.5, x_range=(0.2, 0.4))
    assert arm_only == pytest.approx(2 * math.pi * 0.05, rel=0.02)
    assert hull_all > arm_only


def test_narrowest_and_fullest_slices():
    m = hourglass(0.16, 0.12, 0.17, 1.0)
    assert narrowest_slice_y(m, 0.05, 0.95, steps=19) == pytest.approx(0.5, abs=0.06)
    assert fullest_slice_y(m, 0.05, 0.95, steps=19) < 0.2


def test_path_length():
    pts = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0]], dtype=float)
    assert path_length(pts) == pytest.approx(2.0)
    assert path_length(pts[:1]) == 0.0


def test_measure_body_on_synthetic_body():
    torso = cylinder(0.15, 1.0)
    lm = BodyLandmarks(
        floor_y=-0.8,
        crown_y=1.0,
        neck_base_y=0.95,
        chest_y=0.7,
        waist_y=0.4,
        hip_y=0.1,
        bicep_y=0.6,
        left_shoulder=np.array([-0.22, 0.9, 0.0]),
        right_shoulder=np.array([0.22, 0.9, 0.0]),
        left_wrist=np.array([-0.22, 0.3, 0.0]),
        neck_base_back=np.array([0.0, 0.95, -0.15]),
        waist_back=np.array([0.0, 0.5, -0.15]),
        left_arm_x_range=(-0.4, -0.18),  # nothing there in this synthetic torso
    )
    m = measure_body(torso, lm)
    assert set(m) == set(BodyField)
    assert m[BodyField.HEIGHT] == pytest.approx(180.0)
    assert m[BodyField.CHEST] == pytest.approx(2 * math.pi * 15, rel=0.01)
    assert m[BodyField.SHOULDER] == pytest.approx(44.0)
    assert m[BodyField.ARM_LENGTH] == pytest.approx(60.0)
    assert m[BodyField.BACK_LENGTH] == pytest.approx(45.0)
    assert m[BodyField.BICEP] == 0.0  # no arm geometry in the synthetic mesh


def test_mesh_shape_validation():
    with pytest.raises(ValueError):
        Mesh(np.zeros((3, 2)), np.zeros((1, 3), dtype=np.int64))
    with pytest.raises(ValueError):
        Mesh(np.zeros((3, 3)), np.zeros((1, 4), dtype=np.int64))
