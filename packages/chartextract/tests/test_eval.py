from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

EVAL_SCRIPT = Path(__file__).resolve().parents[1] / "eval" / "run_eval.py"


def _load_eval_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_eval", EVAL_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_eval"] = module
    spec.loader.exec_module(module)
    return module


def test_fake_eval_scores_everything() -> None:
    run_eval = _load_eval_module()
    scores = run_eval.run(fake=True)
    assert len(scores) == 5
    assert all(not s.errors for s in scores), [s.errors for s in scores]
    total = sum(s.cells_expected for s in scores)
    assert total > 0 and sum(s.cells_correct for s in scores) == total
    assert all(s.classification_ok for s in scores)
    text = run_eval.report(scores, model="claude-opus-5-5")
    assert "cell accuracy" in text and "(100.0%)" in text
    assert "per domain:" in text
    assert "estimated cost" in text


def test_cost_estimate_uses_price_table() -> None:
    run_eval = _load_eval_module()
    assert run_eval.estimate_cost("claude-opus-5-5", 1_000_000, 100_000) == 4.0 + 2.0
    assert run_eval.estimate_cost("unknown-model", 1_000_000, 0) == 4.0


def test_eval_main_fake_exit_code() -> None:
    run_eval = _load_eval_module()
    assert run_eval.main(["--fake"]) == 0
