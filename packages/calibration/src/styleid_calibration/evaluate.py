"""Mean absolute error per field and the proposal's accuracy gates."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from styleid_bodyfit.correction import CorrectionModel
from styleid_fit.types import BodyField, Source

from .data import Pair


@dataclass(frozen=True)
class Gate:
    path: Source
    fields: tuple[BodyField, ...]
    max_mae_cm: float


#: From the proposal: LiDAR chest/waist ≤ 1.5 cm MAE, photo path ≤ 2.5 cm.
GATES: tuple[Gate, ...] = (
    Gate(Source.LIDAR, (BodyField.CHEST, BodyField.WAIST), 1.5),
    Gate(Source.PHOTO, (BodyField.CHEST, BodyField.WAIST), 2.5),
)


def mae_by_field(
    pairs: Sequence[Pair], correction: CorrectionModel | None = None
) -> dict[BodyField, float]:
    correction = correction or CorrectionModel.identity()
    out: dict[BodyField, float] = {}
    for f in BodyField:
        errs = [
            abs(correction.apply({f: p.scan[f]})[f] - p.tape[f])
            for p in pairs
            if f in p.scan and f in p.tape
        ]
        if errs:
            out[f] = round(float(np.mean(errs)), 2)
    return out


@dataclass(frozen=True)
class GateResult:
    gate: Gate
    mae_cm: Mapping[BodyField, float]
    passed: bool


def evaluate(
    pairs: Sequence[Pair], path: Source, correction: CorrectionModel | None = None
) -> list[GateResult]:
    mae = mae_by_field(pairs, correction)
    results = []
    for g in GATES:
        if g.path is not path:
            continue
        sub = {f: mae[f] for f in g.fields if f in mae}
        passed = bool(sub) and all(v <= g.max_mae_cm for v in sub.values())
        results.append(GateResult(g, sub, passed))
    return results
