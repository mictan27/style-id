"""Tape-equivalent measurements from a body mesh.

Circumferences are the perimeter of the convex hull of a horizontal slice,
because a tape bridges hollows rather than following them. Lengths are
straight-line or summed-segment distances between landmark points.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from styleid_fit.types import BodyField

Vec = NDArray[np.float64]


@dataclass(frozen=True)
class Mesh:
    """Vertices (N, 3) in metres, Y up; faces (M, 3) vertex indices."""

    vertices: Vec
    faces: NDArray[np.int64]

    def __post_init__(self) -> None:
        if self.vertices.ndim != 2 or self.vertices.shape[1] != 3:
            raise ValueError("vertices must be (N, 3)")
        if self.faces.ndim != 2 or self.faces.shape[1] != 3:
            raise ValueError("faces must be (M, 3)")


def _plane_segments(mesh: Mesh, y: float) -> Vec:
    """Points where triangle edges cross the plane Y = y, as (K, 2) XZ coordinates."""
    v = mesh.vertices[mesh.faces]  # (M, 3, 3)
    pts: list[Vec] = []
    for a, b in ((0, 1), (1, 2), (2, 0)):
        pa, pb = v[:, a, :], v[:, b, :]
        ya, yb = pa[:, 1] - y, pb[:, 1] - y
        crossing = (ya * yb) < 0
        if not np.any(crossing):
            continue
        t = ya[crossing] / (ya[crossing] - yb[crossing])
        p = pa[crossing] + (pb[crossing] - pa[crossing]) * t[:, None]
        pts.append(p[:, [0, 2]])
    if not pts:
        return np.empty((0, 2))
    return np.concatenate(pts, axis=0)


def convex_hull_2d(points: Vec) -> Vec:
    """Andrew's monotone chain. Returns hull vertices in counter-clockwise order."""
    if len(points) < 3:
        return points
    pts = np.unique(points, axis=0)
    if len(pts) < 3:
        return pts
    order = np.lexsort((pts[:, 1], pts[:, 0]))
    pts = pts[order]

    def cross(o: Vec, a: Vec, b: Vec) -> float:
        return float((a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]))

    lower: list[Vec] = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list[Vec] = []
    for p in pts[::-1]:
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return np.asarray(lower[:-1] + upper[:-1])


def perimeter(polygon: Vec) -> float:
    if len(polygon) < 2:
        return 0.0
    d = np.diff(np.vstack([polygon, polygon[:1]]), axis=0)
    return float(np.sum(np.hypot(d[:, 0], d[:, 1])))


def slice_perimeter(mesh: Mesh, y: float, *, x_range: tuple[float, float] | None = None) -> float:
    """Convex-hull perimeter of the slice at height y, in the mesh's units.

    `x_range` restricts the slice to one limb (e.g. the left upper arm) so a
    bicep slice does not hull together with the torso.
    """
    pts = _plane_segments(mesh, y)
    if x_range is not None:
        lo, hi = x_range
        pts = pts[(pts[:, 0] >= lo) & (pts[:, 0] <= hi)]
    return perimeter(convex_hull_2d(pts))


def path_length(points: Vec) -> float:
    """Summed segment length through an ordered list of 3D points."""
    if len(points) < 2:
        return 0.0
    return float(np.sum(np.linalg.norm(np.diff(points, axis=0), axis=1)))


@dataclass(frozen=True)
class BodyLandmarks:
    """Landmark positions in mesh units, supplied by the fitter from MHR joints.

    Heights are Y values of slicing planes. Points are 3D.
    """

    floor_y: float
    crown_y: float
    neck_base_y: float
    chest_y: float
    waist_y: float
    hip_y: float
    bicep_y: float
    left_shoulder: Vec
    right_shoulder: Vec
    left_wrist: Vec
    neck_base_back: Vec
    waist_back: Vec
    #: X extent of the left upper arm at bicep height, to isolate it from the torso.
    left_arm_x_range: tuple[float, float]
    #: Points along the shoulder surface from left to right shoulder point (optional).
    shoulder_path: Vec | None = None


def measure_body(
    mesh: Mesh, lm: BodyLandmarks, *, scale_to_cm: float = 100.0
) -> Mapping[BodyField, float]:
    """The nine measurements, in cm."""
    shoulder_pts = (
        lm.shoulder_path
        if lm.shoulder_path is not None
        else np.vstack([lm.left_shoulder, lm.right_shoulder])
    )
    m = {
        BodyField.HEIGHT: lm.crown_y - lm.floor_y,
        BodyField.NECK: slice_perimeter(mesh, lm.neck_base_y),
        BodyField.SHOULDER: path_length(shoulder_pts),
        BodyField.CHEST: slice_perimeter(mesh, lm.chest_y),
        BodyField.WAIST: slice_perimeter(mesh, lm.waist_y),
        BodyField.HIP: slice_perimeter(mesh, lm.hip_y),
        BodyField.ARM_LENGTH: float(np.linalg.norm(lm.left_wrist - lm.left_shoulder)),
        BodyField.BICEP: slice_perimeter(mesh, lm.bicep_y, x_range=lm.left_arm_x_range),
        BodyField.BACK_LENGTH: float(np.linalg.norm(lm.waist_back - lm.neck_base_back)),
    }
    return {k: round(v * scale_to_cm, 1) for k, v in m.items()}


def narrowest_slice_y(mesh: Mesh, y_lo: float, y_hi: float, steps: int = 20) -> float:
    """Height of the smallest convex-hull perimeter between two heights (the natural waist)."""
    ys = np.linspace(y_lo, y_hi, steps)
    perims = [slice_perimeter(mesh, float(y)) for y in ys]
    return float(ys[int(np.argmin(perims))])


def fullest_slice_y(mesh: Mesh, y_lo: float, y_hi: float, steps: int = 20) -> float:
    """Height of the largest convex-hull perimeter between two heights (chest or hips)."""
    ys = np.linspace(y_lo, y_hi, steps)
    perims = [slice_perimeter(mesh, float(y)) for y in ys]
    return float(ys[int(np.argmax(perims))])
