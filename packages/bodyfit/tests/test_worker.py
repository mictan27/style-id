import json

import pytest

from styleid_bodyfit import (
    Correction,
    CorrectionModel,
    FakeFitter,
    ScanUpload,
    process_scan,
)
from styleid_bodyfit.fitter import Sam3dFitter
from styleid_fit.types import BodyField, Confidence, Source


@pytest.fixture
def upload(tmp_path):
    d = tmp_path / "scan-123"
    d.mkdir()
    (d / "manifest.json").write_text(json.dumps({"keyframe_count": 40}))
    (d / "kf_000.jpg").write_bytes(b"\xff\xd8fake")
    return ScanUpload(path=d, source=Source.LIDAR)


def test_fake_fitter_lidar(upload):
    body = process_scan(upload, FakeFitter.average_adult(), delete_upload=False)
    assert body.source is Source.LIDAR
    assert body.measurements[BodyField.CHEST].value_cm == 96.0
    assert body.measurements[BodyField.CHEST].source is Source.LIDAR
    assert body.measurements[BodyField.CHEST].confidence is Confidence.MEDIUM
    assert upload.path.exists()


def test_upload_is_deleted_after_fit(upload):
    process_scan(upload, FakeFitter.average_adult())
    assert not upload.path.exists()


def test_upload_is_deleted_even_when_fit_fails(upload):
    with pytest.raises(NotImplementedError):
        process_scan(upload, Sam3dFitter(upload.path / "weights"))
    assert not upload.path.exists()


def test_photo_path_scales_to_typed_height_and_is_low_confidence(tmp_path):
    d = tmp_path / "photo"
    d.mkdir()
    up = ScanUpload(path=d, source=Source.PHOTO, height_cm=192.5)
    body = process_scan(up, FakeFitter.average_adult())
    assert body.measurements[BodyField.HEIGHT].value_cm == 192.5
    assert body.measurements[BodyField.HEIGHT].source is Source.MANUAL
    assert body.measurements[BodyField.CHEST].value_cm == pytest.approx(96 * 192.5 / 175, abs=0.1)
    assert body.measurements[BodyField.CHEST].confidence is Confidence.LOW


def test_correction_model_roundtrip_and_apply(tmp_path):
    model = CorrectionModel({BodyField.CHEST: Correction(a=0.98, b=1.5, mae_cm=1.1, n=80)})
    p = tmp_path / "corr.json"
    model.dump(p)
    loaded = CorrectionModel.load(p)
    assert loaded.by_field[BodyField.CHEST].a == 0.98
    out = loaded.apply({BodyField.CHEST: 100.0, BodyField.WAIST: 80.0})
    assert out[BodyField.CHEST] == pytest.approx(99.5)
    assert out[BodyField.WAIST] == 80.0  # identity for fields without a correction


def test_manifest_missing_is_tolerated(tmp_path):
    up = ScanUpload(path=tmp_path, source=Source.LIDAR)
    assert up.manifest == {}
    assert up.keyframe_count == 0
