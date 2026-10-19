"""Per-measurement correction learned from the calibration study: tape ≈ a·mesh + b."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from styleid_fit.types import BodyField


@dataclass(frozen=True)
class Correction:
    a: float = 1.0
    b: float = 0.0
    mae_cm: float | None = None
    n: int = 0

    def apply(self, x: float) -> float:
        return self.a * x + self.b


@dataclass(frozen=True)
class CorrectionModel:
    by_field: Mapping[BodyField, Correction]

    @classmethod
    def identity(cls) -> CorrectionModel:
        return cls({})

    @classmethod
    def load(cls, path: Path) -> CorrectionModel:
        raw = json.loads(path.read_text())
        return cls(
            {
                BodyField(k): Correction(
                    a=float(v["a"]), b=float(v["b"]), mae_cm=v.get("mae_cm"), n=int(v.get("n", 0))
                )
                for k, v in raw.items()
            }
        )

    def dump(self, path: Path) -> None:
        path.write_text(
            json.dumps(
                {
                    k.value: {"a": c.a, "b": c.b, "mae_cm": c.mae_cm, "n": c.n}
                    for k, c in self.by_field.items()
                },
                indent=2,
            )
            + "\n"
        )

    def apply(self, measurements: Mapping[BodyField, float]) -> dict[BodyField, float]:
        return {
            f: round(self.by_field.get(f, Correction()).apply(v), 1)
            for f, v in measurements.items()
        }
