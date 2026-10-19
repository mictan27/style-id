"""CSV formats for the calibration study.

tape.csv:  subject_id, measurer, date, then the nine body fields in cm
           (height, neck, shoulder, chest, waist, hip, arm_length, bicep, back_length)
scans.csv: subject_id, path (lidar|photo), scan_id, then the same nine fields, uncorrected
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from styleid_fit.types import BodyField, Source

FIELDS: tuple[BodyField, ...] = tuple(BodyField)


@dataclass(frozen=True)
class TapeRow:
    subject_id: str
    measurer: str
    date: str
    values: Mapping[BodyField, float]


@dataclass(frozen=True)
class ScanRow:
    subject_id: str
    path: Source
    scan_id: str
    values: Mapping[BodyField, float]


def _values(row: Mapping[str, str]) -> dict[BodyField, float]:
    out: dict[BodyField, float] = {}
    for f in FIELDS:
        raw = (row.get(f.value) or "").strip()
        if raw:
            out[f] = float(raw)
    return out


def read_tape(path: Path) -> list[TapeRow]:
    with path.open(newline="") as fh:
        return [
            TapeRow(r["subject_id"], r.get("measurer", ""), r.get("date", ""), _values(r))
            for r in csv.DictReader(fh)
        ]


def read_scans(path: Path) -> list[ScanRow]:
    with path.open(newline="") as fh:
        return [
            ScanRow(r["subject_id"], Source(r["path"]), r.get("scan_id", ""), _values(r))
            for r in csv.DictReader(fh)
        ]


@dataclass(frozen=True)
class Pair:
    subject_id: str
    tape: Mapping[BodyField, float]
    scan: Mapping[BodyField, float]


def pair(tape: Iterable[TapeRow], scans: Iterable[ScanRow], path: Source) -> list[Pair]:
    """Join tape and scan rows by subject for one capture path.

    Subjects missing either side are dropped.
    """
    by_subject = {t.subject_id: t for t in tape}
    out: list[Pair] = []
    for s in scans:
        if s.path is not path:
            continue
        t = by_subject.get(s.subject_id)
        if t is None:
            continue
        out.append(Pair(s.subject_id, t.values, s.values))
    return out
