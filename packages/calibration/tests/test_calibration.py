import csv
import random

import pytest

from styleid_bodyfit.correction import CorrectionModel
from styleid_calibration import (
    evaluate,
    mae_by_field,
    pair,
    read_scans,
    read_tape,
    train_correction,
)
from styleid_calibration.__main__ import main
from styleid_calibration.data import Pair
from styleid_fit.types import BodyField, Source

FIELDS = [f.value for f in BodyField]


def synthetic(n=40, *, bias=3.0, scale=0.97, noise=0.4, seed=1):
    """Tape truth plus a scan that underestimates: scan = scale*tape - bias + noise."""
    rng = random.Random(seed)
    tape, scans = [], []
    for i in range(n):
        sid = f"S{i:03d}"
        truth = {f: rng.uniform(30, 110) for f in BodyField}
        truth[BodyField.HEIGHT] = rng.uniform(150, 195)
        tape.append(
            {
                "subject_id": sid,
                "measurer": "A",
                "date": "2026-11-01",
                **{f.value: f"{v:.1f}" for f, v in truth.items()},
            }
        )
        scan = {f: scale * v - bias + rng.gauss(0, noise) for f, v in truth.items()}
        scans.append(
            {
                "subject_id": sid,
                "path": "lidar",
                "scan_id": f"L{i}",
                **{f.value: f"{v:.1f}" for f, v in scan.items()},
            }
        )
        if i % 2 == 0:  # photo scans for half the subjects, noisier
            photo = {f: scale * v - bias + rng.gauss(0, 2.0) for f, v in truth.items()}
            scans.append(
                {
                    "subject_id": sid,
                    "path": "photo",
                    "scan_id": f"P{i}",
                    **{f.value: f"{v:.1f}" for f, v in photo.items()},
                }
            )
    return tape, scans


def write(tmp_path, tape, scans):
    tp, sp = tmp_path / "tape.csv", tmp_path / "scans.csv"
    with tp.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["subject_id", "measurer", "date", *FIELDS])
        w.writeheader()
        w.writerows(tape)
    with sp.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["subject_id", "path", "scan_id", *FIELDS])
        w.writeheader()
        w.writerows(scans)
    return tp, sp


def test_read_and_pair(tmp_path):
    tp, sp = write(tmp_path, *synthetic(10))
    tape, scans = read_tape(tp), read_scans(sp)
    assert len(tape) == 10 and len(scans) == 15
    lidar = pair(tape, scans, Source.LIDAR)
    photo = pair(tape, scans, Source.PHOTO)
    assert len(lidar) == 10 and len(photo) == 5
    assert set(lidar[0].tape) == set(BodyField)


def test_pair_drops_unmatched():
    from styleid_calibration.data import ScanRow, TapeRow

    t = [TapeRow("A", "", "", {BodyField.CHEST: 96})]
    s = [
        ScanRow("A", Source.LIDAR, "", {BodyField.CHEST: 93}),
        ScanRow("B", Source.LIDAR, "", {BodyField.CHEST: 90}),
    ]
    assert [p.subject_id for p in pair(t, s, Source.LIDAR)] == ["A"]


def test_training_recovers_the_systematic_error(tmp_path):
    tp, sp = write(tmp_path, *synthetic(40, bias=3.0, scale=0.97))
    pairs = pair(read_tape(tp), read_scans(sp), Source.LIDAR)
    model = train_correction(pairs)
    chest = model.by_field[BodyField.CHEST]
    # tape = (scan + 3) / 0.97 -> a ≈ 1.031, b ≈ 3.09
    assert chest.a == pytest.approx(1 / 0.97, abs=0.02)
    assert chest.b == pytest.approx(3 / 0.97, abs=1.0)
    assert chest.n == 40
    before = mae_by_field(pairs)[BodyField.CHEST]
    after = mae_by_field(pairs, model)[BodyField.CHEST]
    assert after < before and after < 0.8


def test_too_few_pairs_keeps_identity():
    pairs = [Pair(str(i), {BodyField.CHEST: 100.0}, {BodyField.CHEST: 97.0}) for i in range(3)]
    assert train_correction(pairs).by_field == {}


def test_gates(tmp_path):
    tp, sp = write(tmp_path, *synthetic(40))
    tape, scans = read_tape(tp), read_scans(sp)
    lidar = pair(tape, scans, Source.LIDAR)
    assert not evaluate(lidar, Source.LIDAR)[0].passed  # 3 cm bias fails 1.5 cm gate
    model = train_correction(lidar)
    assert evaluate(lidar, Source.LIDAR, model)[0].passed
    photo = pair(tape, scans, Source.PHOTO)
    res = evaluate(photo, Source.PHOTO, train_correction(photo))
    assert res[0].gate.max_mae_cm == 2.5


def test_cli_train_then_evaluate(tmp_path, capsys):
    tp, sp = write(tmp_path, *synthetic(30))
    out = tmp_path / "corr.json"
    assert (
        main(["train", "--tape", str(tp), "--scans", str(sp), "--path", "lidar", "--out", str(out)])
        == 0
    )
    assert CorrectionModel.load(out).by_field[BodyField.WAIST].n == 30
    assert main(["evaluate", "--tape", str(tp), "--scans", str(sp), "--path", "lidar"]) == 1
    assert (
        main(
            [
                "evaluate",
                "--tape",
                str(tp),
                "--scans",
                str(sp),
                "--path",
                "lidar",
                "--correction",
                str(out),
            ]
        )
        == 0
    )
    assert "gate PASS" in capsys.readouterr().out
