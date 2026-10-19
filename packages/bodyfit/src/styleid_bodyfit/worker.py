"""Process one scan: fit, correct, build the body record, delete the raw upload."""

from __future__ import annotations

import shutil
from pathlib import Path

from styleid_fit.types import BodyField, Source
from styleid_schema import BodyModel, MeasurementModel

from .correction import CorrectionModel
from .fitter import Fitter, ScanUpload


def process_scan(
    upload: ScanUpload,
    fitter: Fitter,
    correction: CorrectionModel | None = None,
    *,
    delete_upload: bool = True,
) -> BodyModel:
    """Fit the scan and return a BodyModel. The raw upload is deleted whether the fit
    succeeds or raises, which is the privacy promise in the proposal."""
    correction = correction or CorrectionModel.identity()
    try:
        result = fitter.fit(upload)
        corrected = correction.apply(result.measurements)
        measurements = {
            f: MeasurementModel(value_cm=v, source=upload.source, confidence=result.confidence)
            for f, v in corrected.items()
        }
        if upload.height_cm is not None:
            measurements[BodyField.HEIGHT] = MeasurementModel(
                value_cm=upload.height_cm, source=Source.MANUAL, confidence=result.confidence
            )
        return BodyModel(source=upload.source, measurements=measurements)
    finally:
        if delete_upload:
            _delete(upload.path)


def _delete(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    elif path.exists():
        path.unlink(missing_ok=True)
