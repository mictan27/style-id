import numpy as np
import pytest

from styleid_bodyfit.losses import (
    keypoint_reprojection_loss,
    one_sided_depth_loss,
    shape_prior_loss,
    silhouette_iou_loss,
    temporal_smoothness_loss,
)


def ring(r: float, n: int = 64) -> np.ndarray:
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.stack([r * np.cos(a), np.zeros(n), r * np.sin(a)], axis=1)


def test_depth_loss_is_one_sided():
    cloth = ring(0.20)  # observed surface (clothes)
    inside = one_sided_depth_loss(ring(0.18), cloth)
    outside = one_sided_depth_loss(ring(0.22), cloth)
    on = one_sided_depth_loss(ring(0.20), cloth)
    assert on == pytest.approx(0.0, abs=1e-9)
    assert inside > 0 and outside > 0
    assert outside > 5 * inside  # same 2 cm offset, penalised ~10x when outside


def test_depth_loss_empty_inputs():
    assert one_sided_depth_loss(np.empty((0, 3)), ring(0.2)) == 0.0
    assert one_sided_depth_loss(ring(0.2), np.empty((0, 3))) == 0.0


def test_keypoint_loss_weights_by_confidence():
    proj = np.array([[0.0, 0.0], [10.0, 10.0]])
    obs = np.array([[0.0, 0.0], [10.0, 14.0]])
    assert keypoint_reprojection_loss(proj, obs, np.array([1.0, 1.0])) == pytest.approx(8.0)
    assert keypoint_reprojection_loss(proj, obs, np.array([1.0, 0.0])) == pytest.approx(0.0)
    assert keypoint_reprojection_loss(np.empty((0, 2)), np.empty((0, 2)), np.empty(0)) == 0.0


def test_silhouette_loss():
    a = np.zeros((4, 4), dtype=bool)
    a[:2] = True
    b = np.zeros((4, 4), dtype=bool)
    b[1:3] = True
    assert silhouette_iou_loss(a, a) == 0.0
    assert silhouette_iou_loss(a, b) == pytest.approx(1 - 4 / 12)
    assert silhouette_iou_loss(np.zeros((2, 2), bool), np.zeros((2, 2), bool)) == 0.0


def test_priors():
    assert shape_prior_loss(np.zeros(10)) == 0.0
    assert shape_prior_loss(np.ones(4), weight=0.5) == pytest.approx(2.0)
    assert temporal_smoothness_loss(np.array([[0.0, 0.0]])) == 0.0
    assert temporal_smoothness_loss(
        np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 0.0]])
    ) == pytest.approx(0.5)
