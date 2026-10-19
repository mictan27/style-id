"""Reference (numpy) implementations of the fitting losses.

The GPU optimiser mirrors these in PyTorch; keeping a numpy twin makes the
semantics testable on CPU. All inputs are in metres.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

Arr = NDArray[np.float64]


def one_sided_depth_loss(
    mesh_points: Arr,
    depth_points: Arr,
    *,
    outside_weight: float = 10.0,
    inside_weight: float = 1.0,
) -> float:
    """Penalise body surface outside the observed cloud heavily, inside it lightly.

    Depth sees clothing, not skin, so the true body lies on or inside the
    observed surface. For each mesh point take the nearest depth point; the
    signed distance along the depth point's outward direction (approximated by
    the vector from the cloud centroid) decides which side it is on.
    """
    if len(mesh_points) == 0 or len(depth_points) == 0:
        return 0.0
    centroid = depth_points.mean(axis=0)
    d = mesh_points[:, None, :] - depth_points[None, :, :]
    dist2 = np.einsum("ijk,ijk->ij", d, d)
    nearest = np.argmin(dist2, axis=1)
    nearest_pts = depth_points[nearest]
    outward = nearest_pts - centroid
    norms = np.linalg.norm(outward, axis=1, keepdims=True)
    outward = np.divide(outward, norms, out=np.zeros_like(outward), where=norms > 0)
    signed = np.einsum("ij,ij->i", mesh_points - nearest_pts, outward)
    outside = np.clip(signed, 0, None)
    inside = np.clip(-signed, 0, None)
    return float(np.mean(outside_weight * outside**2 + inside_weight * inside**2))


def keypoint_reprojection_loss(
    projected: Arr,
    observed: Arr,
    confidence: Arr,
) -> float:
    """Confidence-weighted squared pixel error between projected joints and 2D keypoints."""
    if len(projected) == 0:
        return 0.0
    err = np.sum((projected - observed) ** 2, axis=1)
    w = np.clip(confidence, 0, 1)
    return float(np.sum(w * err) / max(float(np.sum(w)), 1e-9))


def silhouette_iou_loss(pred_mask: NDArray[np.bool_], obs_mask: NDArray[np.bool_]) -> float:
    """1 - IoU between the rendered body mask and the person segmentation mask."""
    inter = np.logical_and(pred_mask, obs_mask).sum()
    union = np.logical_or(pred_mask, obs_mask).sum()
    if union == 0:
        return 0.0
    return float(1.0 - inter / union)


def shape_prior_loss(betas: Arr, weight: float = 1e-3) -> float:
    """L2 regulariser keeping shape parameters near the population mean."""
    return float(weight * np.sum(betas**2))


def temporal_smoothness_loss(poses: Arr, weight: float = 1.0) -> float:
    """Discourage pose jitter between consecutive keyframes. poses: (T, P)."""
    if len(poses) < 2:
        return 0.0
    return float(weight * np.mean(np.sum(np.diff(poses, axis=0) ** 2, axis=1)))
