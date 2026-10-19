"""The Fitter seam: real GPU fitter and a fake for local runs."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from styleid_fit.types import BodyField, Confidence, Source


@dataclass(frozen=True)
class ScanUpload:
    """A scan as uploaded by the phone: a directory with manifest.json and keyframes."""

    path: Path
    source: Source  # LIDAR or PHOTO
    height_cm: float | None = None  # typed by the user on the photo path; fixes scale

    @property
    def manifest(self) -> dict[str, object]:
        p = self.path / "manifest.json"
        if not p.exists():
            return {}
        return dict(json.loads(p.read_text()))

    @property
    def keyframe_count(self) -> int:
        n = self.manifest.get("keyframe_count")
        return int(n) if isinstance(n, int | float | str) and str(n).isdigit() else 0


@dataclass(frozen=True)
class FitResult:
    measurements: Mapping[BodyField, float]  # cm, before correction
    confidence: Confidence
    shape_params: tuple[float, ...] = ()
    mesh_path: Path | None = None
    diagnostics: Mapping[str, float] = field(default_factory=dict)


class Fitter(Protocol):
    def fit(self, upload: ScanUpload) -> FitResult: ...


@dataclass(frozen=True)
class FakeFitter:
    """Returns a fixed body. Used by the API, the worker and tests when there is no GPU."""

    measurements: Mapping[BodyField, float]
    confidence: Confidence = Confidence.MEDIUM

    @classmethod
    def average_adult(cls) -> FakeFitter:
        return cls(
            {
                BodyField.HEIGHT: 175.0,
                BodyField.NECK: 38.5,
                BodyField.SHOULDER: 44.0,
                BodyField.CHEST: 96.0,
                BodyField.WAIST: 84.0,
                BodyField.HIP: 98.0,
                BodyField.ARM_LENGTH: 61.0,
                BodyField.BICEP: 31.0,
                BodyField.BACK_LENGTH: 46.0,
            }
        )

    def fit(self, upload: ScanUpload) -> FitResult:
        m = dict(self.measurements)
        if upload.height_cm is not None and BodyField.HEIGHT in m and m[BodyField.HEIGHT] > 0:
            # The photo path fixes scale with the typed height.
            k = upload.height_cm / m[BodyField.HEIGHT]
            m = {f: round(v * k, 1) for f, v in m.items()}
        conf = Confidence.LOW if upload.source is Source.PHOTO else self.confidence
        return FitResult(
            measurements=m, confidence=conf, diagnostics={"keyframes": upload.keyframe_count}
        )


class Sam3dFitter:
    """SAM 3D Body → MHR initialisation → multi-frame optimisation on a GPU.

    Pipeline (see docs/adr and the proposal):
    1. Run SAM 3D Body on 3 to 5 keyframes for an initial MHR shape and per-frame pose.
    2. Optimise one shared shape, per-frame pose and scale against depth points
       (one-sided loss), 2D keypoints and silhouettes, with a shape prior and
       temporal smoothness (see losses.py for the reference definitions).
    3. Measure the fitted mesh (measure.py) and return the nine values.

    Not implemented on this machine: it needs torch, the SAM 3D Body weights and a GPU.
    """

    def __init__(self, weights_dir: Path, device: str = "cuda") -> None:
        self.weights_dir = weights_dir
        self.device = device

    def fit(self, upload: ScanUpload) -> FitResult:
        raise NotImplementedError(
            "Sam3dFitter needs torch, SAM 3D Body weights and a GPU; use FakeFitter locally"
        )
