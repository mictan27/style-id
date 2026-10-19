"""CLI: train a correction model or evaluate one against the gates.

python -m styleid_calibration train --tape tape.csv --scans scans.csv --path lidar --out corr.json
python -m styleid_calibration evaluate --tape tape.csv --scans scans.csv --path lidar \
    [--correction corr.json]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from styleid_bodyfit.correction import CorrectionModel
from styleid_fit.types import Source

from .data import pair, read_scans, read_tape
from .evaluate import evaluate, mae_by_field
from .train import train_correction


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="styleid_calibration")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("train", "evaluate"):
        p = sub.add_parser(name)
        p.add_argument("--tape", type=Path, required=True)
        p.add_argument("--scans", type=Path, required=True)
        p.add_argument("--path", choices=["lidar", "photo"], required=True)
        if name == "train":
            p.add_argument("--out", type=Path, required=True)
        else:
            p.add_argument("--correction", type=Path)
    ns = ap.parse_args(argv)
    pairs = pair(read_tape(ns.tape), read_scans(ns.scans), Source(ns.path))
    print(f"{len(pairs)} paired subjects on the {ns.path} path")
    if ns.cmd == "train":
        model = train_correction(pairs)
        model.dump(ns.out)
        for f, c in model.by_field.items():
            print(f"  {f.value:12s} a={c.a:.4f} b={c.b:+.2f} loo_mae={c.mae_cm} n={c.n}")
        return 0
    corr = CorrectionModel.load(ns.correction) if ns.correction else None
    for f, v in mae_by_field(pairs, corr).items():
        print(f"  {f.value:12s} MAE {v:.2f} cm")
    ok = True
    for r in evaluate(pairs, Source(ns.path), corr):
        status = "PASS" if r.passed else "FAIL"
        ok &= r.passed
        fields = ", ".join(f.value for f in r.gate.fields)
        print(f"gate {status}: {fields} <= {r.gate.max_mae_cm} cm -> {r.mae_cm}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
