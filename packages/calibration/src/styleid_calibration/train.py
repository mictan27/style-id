"""Fit tape ≈ a·scan + b per measurement, with leave-one-out error."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from styleid_bodyfit.correction import Correction, CorrectionModel
from styleid_fit.types import BodyField

from .data import Pair

MIN_PAIRS = 5


def _fit_line(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    a, b = np.polyfit(x, y, 1)
    return float(a), float(b)


def _loo_mae(x: np.ndarray, y: np.ndarray) -> float:
    errs = []
    for i in range(len(x)):
        mask = np.arange(len(x)) != i
        a, b = _fit_line(x[mask], y[mask])
        errs.append(abs(a * x[i] + b - y[i]))
    return float(np.mean(errs))


def train_correction(pairs: Sequence[Pair], *, min_pairs: int = MIN_PAIRS) -> CorrectionModel:
    """One linear correction per field. Fields with too few pairs keep the identity."""
    out: dict[BodyField, Correction] = {}
    for f in BodyField:
        xs = [p.scan[f] for p in pairs if f in p.scan and f in p.tape]
        ys = [p.tape[f] for p in pairs if f in p.scan and f in p.tape]
        if len(xs) < min_pairs:
            continue
        x, y = np.asarray(xs, dtype=float), np.asarray(ys, dtype=float)
        a, b = _fit_line(x, y)
        out[f] = Correction(
            a=round(a, 4), b=round(b, 3), mae_cm=round(_loo_mae(x, y), 2), n=len(xs)
        )
    return CorrectionModel(out)
