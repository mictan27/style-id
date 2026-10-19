"""Run the chart pipeline over the labelled pages and score it.

    uv run python packages/chartextract/eval/run_eval.py           # Claude (needs API key)
    uv run python packages/chartextract/eval/run_eval.py --fake    # recorded extraction.json
    uv run python packages/chartextract/eval/run_eval.py --record  # Claude + refresh fixtures

A cell is correct when the field exists in the prediction and |diff| <= 0.5 cm. Classification is
correct when chart_kind, measure_basis and unit all match.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from styleid_charts import (
    DEFAULT_MODEL,
    ClaudeExtractor,
    Extractor,
    FakeExtractor,
    ProductExtraction,
    StaticFetcher,
    extract_product,
    load_recorded,
)
from styleid_schema import GarmentKind

LABELLED_DIR = Path(__file__).parent / "labelled"
CELL_TOLERANCE_CM = 0.5

#: USD per million tokens (input, output). Unknown models fall back to Opus pricing.
PRICES: dict[str, tuple[float, float]] = {
    "claude-opus-5-5": (4.0, 20.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-fable-5-1": (10.0, 50.0),
}


@dataclass
class PageScore:
    """Per-page scoring detail."""

    page_id: str
    domain: str
    status_expected: str
    status_actual: str
    classification_ok: bool
    cells_expected: int = 0
    cells_correct: int = 0
    cells_extra: int = 0
    flags_ok: bool = True
    tokens_in: int = 0
    tokens_out: int = 0
    errors: list[str] = field(default_factory=list)


def _domain(url: str) -> str:
    """Host without www."""
    return urlsplit(url).netloc.lower().removeprefix("www.")


def _expected_cells(expected: dict[str, Any]) -> dict[tuple[str, str], float]:
    """{(size_label, field): value} from expected.json."""
    return {
        (s["size_label"], f): float(v)
        for s in expected.get("sizes", [])
        for f, v in s.get("measurements", {}).items()
    }


def _actual_cells(result: ProductExtraction) -> dict[tuple[str, str], float]:
    """{(size_label, field): value_cm} from the pipeline output."""
    return {
        (s.size_label or "", f.value): m.value_cm
        for s in result.chart.sizes
        for f, m in s.measurements.items()
    }


def score_page(page_id: str, expected: dict[str, Any], result: ProductExtraction) -> PageScore:
    """Compare one page's result against its expected.json."""
    cls = result.chart.classification
    exp_cls = expected["classification"]
    score = PageScore(
        page_id=page_id,
        domain=_domain(expected["url"]),
        status_expected=expected["status"],
        status_actual=result.chart.status.value,
        classification_ok=(
            cls.chart_kind == exp_cls["chart_kind"]
            and cls.measure_basis == exp_cls["measure_basis"]
            and cls.unit == exp_cls["unit"]
        ),
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
    )
    if score.status_actual != score.status_expected:
        score.errors.append(f"status {score.status_actual} != {score.status_expected}")
    if not score.classification_ok:
        score.errors.append(f"classification {cls.model_dump()} != {exp_cls}")
    exp_stretch = expected.get("stretch")
    act_stretch = result.chart.stretch.value if result.chart.stretch else None
    if exp_stretch is not None and exp_stretch != act_stretch:
        score.errors.append(f"stretch {act_stretch} != {exp_stretch}")

    exp_cells = _expected_cells(expected)
    act_cells = _actual_cells(result)
    score.cells_expected = len(exp_cells)
    for key, value in exp_cells.items():
        actual = act_cells.get(key)
        if actual is not None and abs(actual - value) <= CELL_TOLERANCE_CM:
            score.cells_correct += 1
        else:
            score.errors.append(f"cell {key[0]}/{key[1]}: got {actual}, want {value}")
    score.cells_extra = len(set(act_cells) - set(exp_cells))
    if score.cells_extra:
        score.errors.append(f"{score.cells_extra} unexpected cell(s)")

    actual_flags = {
        s.size_label: (s.length_from_center_back, s.sleeve_from_center_back)
        for s in result.chart.sizes
    }
    for s in expected.get("sizes", []):
        want = (s.get("length_from_center_back", False), s.get("sleeve_from_center_back", False))
        if actual_flags.get(s["size_label"]) != want:
            score.flags_ok = False
            score.errors.append(
                f"CB flags for {s['size_label']}: {actual_flags.get(s['size_label'])}"
            )
    return score


def _extractor_for(page_dir: Path, *, fake: bool, record: bool, model: str | None) -> Extractor:
    """Fake extractor from extraction.json, or Claude (optionally recording)."""
    if fake:
        return FakeExtractor(
            default=load_recorded(page_dir / "extraction.json"), model_id="recorded"
        )
    claude = ClaudeExtractor(model=model)
    if record:
        return _Recorder(claude, page_dir / "extraction.json")
    return claude


class _Recorder:
    """Write the real extraction to a fixed path (RecordingExtractor names files by title)."""

    def __init__(self, inner: Extractor, path: Path) -> None:
        self._inner = inner
        self._path = path

    def extract(self, candidates: Any, *, page_title: str | None) -> Any:
        result = self._inner.extract(candidates, page_title=page_title)
        payload = {
            "page_title": page_title,
            "model_id": result.model_id,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "extraction": result.extraction.model_dump(mode="json"),
        }
        self._path.write_text(json.dumps(payload, indent=2), "utf-8")
        return result


def run(
    labelled_dir: Path = LABELLED_DIR,
    *,
    fake: bool = False,
    record: bool = False,
    model: str | None = None,
    only: str | None = None,
) -> list[PageScore]:
    """Score every labelled page."""
    scores: list[PageScore] = []
    for page_dir in sorted(p for p in labelled_dir.iterdir() if p.is_dir()):
        if only and only not in page_dir.name:
            continue
        expected = json.loads((page_dir / "expected.json").read_text("utf-8"))
        html = (page_dir / "page.html").read_text("utf-8")
        result = extract_product(
            expected["url"],
            fetcher=StaticFetcher(html),
            extractor=_extractor_for(page_dir, fake=fake, record=record, model=model),
            garment_kind=GarmentKind(expected.get("garment_kind", "tee")),
        )
        scores.append(score_page(page_dir.name, expected, result))
    return scores


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """USD for the given token counts at the model's list price."""
    price_in, price_out = PRICES.get(model, PRICES["claude-opus-5-5"])
    return tokens_in / 1e6 * price_in + tokens_out / 1e6 * price_out


def report(scores: list[PageScore], *, model: str) -> str:
    """Human-readable summary."""
    lines: list[str] = []
    total_cells = sum(s.cells_expected for s in scores)
    correct_cells = sum(s.cells_correct for s in scores)
    cls_ok = sum(1 for s in scores if s.classification_ok)
    status_ok = sum(1 for s in scores if s.status_actual == s.status_expected)
    tok_in = sum(s.tokens_in for s in scores)
    tok_out = sum(s.tokens_out for s in scores)
    lines.append(f"pages: {len(scores)}")
    for s in scores:
        mark = "ok " if not s.errors else "ERR"
        lines.append(
            f"  {mark} {s.page_id:<28} cells {s.cells_correct}/{s.cells_expected}"
            f" cls {'y' if s.classification_ok else 'n'} status {s.status_actual}"
        )
        for err in s.errors:
            lines.append(f"        - {err}")
    pct = 100.0 * correct_cells / total_cells if total_cells else 100.0
    lines.append(f"cell accuracy: {correct_cells}/{total_cells} ({pct:.1f}%)")
    lines.append(f"classification accuracy: {cls_ok}/{len(scores)}")
    lines.append(f"status accuracy: {status_ok}/{len(scores)}")
    by_domain: dict[str, list[PageScore]] = defaultdict(list)
    for s in scores:
        by_domain[s.domain].append(s)
    lines.append("per domain:")
    for domain, group in sorted(by_domain.items()):
        exp = sum(g.cells_expected for g in group)
        cor = sum(g.cells_correct for g in group)
        ok = sum(1 for g in group if not g.errors)
        lines.append(f"  {domain:<32} pages ok {ok}/{len(group)}  cells {cor}/{exp}")
    lines.append(f"tokens: in={tok_in} out={tok_out}")
    lines.append(f"estimated cost ({model}): ${estimate_cost(model, tok_in, tok_out):.4f}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--fake", action="store_true", help="use recorded extraction.json (offline)"
    )
    parser.add_argument(
        "--record", action="store_true", help="call Claude and overwrite extraction.json"
    )
    parser.add_argument("--model", default=None, help="override CHART_EXTRACTION_MODEL")
    parser.add_argument("--only", default=None, help="substring filter on page id")
    parser.add_argument("--labelled", type=Path, default=LABELLED_DIR)
    args = parser.parse_args(argv)
    model = args.model or os.environ.get("CHART_EXTRACTION_MODEL") or DEFAULT_MODEL
    scores = run(
        args.labelled, fake=args.fake, record=args.record, model=args.model, only=args.only
    )
    print(report(scores, model=str(model)))
    return 0 if all(not s.errors for s in scores) else 1


if __name__ == "__main__":
    sys.exit(main())
