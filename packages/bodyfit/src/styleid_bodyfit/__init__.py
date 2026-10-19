"""Body-fit worker: scans in, MHR shape + nine tape-equivalent measurements out.

The GPU path (SAM 3D Body → multi-frame optimisation) lives behind the `Fitter`
protocol so the API, queue and app can run against `FakeFitter` without a GPU.
"""

from .correction import Correction, CorrectionModel
from .fitter import FakeFitter, FitResult, Fitter, ScanUpload
from .measure import Mesh, measure_body, slice_perimeter
from .worker import process_scan

__all__ = [
    "Correction",
    "CorrectionModel",
    "FakeFitter",
    "FitResult",
    "Fitter",
    "Mesh",
    "ScanUpload",
    "measure_body",
    "process_scan",
    "slice_perimeter",
]
