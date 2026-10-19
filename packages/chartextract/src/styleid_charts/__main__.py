"""CLI: uv run python -m styleid_charts <url> [--kind tee] [--json]."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from styleid_schema import GarmentKind

from .pipeline import ProductExtraction


def build_parser() -> argparse.ArgumentParser:
    """Argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="styleid_charts", description="Extract a normalised size chart from a product URL."
    )
    parser.add_argument("url", help="product page URL")
    parser.add_argument(
        "--kind",
        choices=[k.value for k in GarmentKind],
        default=GarmentKind.TEE.value,
        help="garment kind (default: tee)",
    )
    parser.add_argument("--json", action="store_true", help="print the NormalisedChart as JSON")
    parser.add_argument("--model", default=None, help="override CHART_EXTRACTION_MODEL")
    parser.add_argument("--no-cache", action="store_true", help="skip the on-disk cache")
    return parser


def format_text(result: ProductExtraction) -> str:
    """Human-readable rendering of a ProductExtraction."""
    chart = result.chart
    lines = [
        f"url:     {result.canonical_url}",
        f"title:   {result.title or '-'}",
        f"brand:   {result.brand_hint or '-'}",
        f"status:  {chart.status.value}" + (" (cached)" if result.from_cache else ""),
        f"kind:    {chart.classification.chart_kind} / {chart.classification.measure_basis}"
        f" / {chart.classification.unit}",
        f"stretch: {chart.stretch.value if chart.stretch else '-'}"
        f"  fabric: {chart.fabric_composition or '-'}",
    ]
    for size in chart.sizes:
        cells = ", ".join(f"{f.value}={m.value_cm:g}" for f, m in size.measurements.items())
        flags = []
        if size.length_from_center_back:
            flags.append("length from CB")
        if size.sleeve_from_center_back:
            flags.append("sleeve from CB")
        suffix = f"  [{'; '.join(flags)}]" if flags else ""
        lines.append(f"  {size.size_label}: {cells}{suffix}")
    for warning in chart.warnings:
        lines.append(f"warning: {warning}")
    if not result.from_cache:
        lines.append(f"tokens:  in={result.tokens_in} out={result.tokens_out}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point; returns a process exit code."""
    args = build_parser().parse_args(argv)
    from pathlib import Path

    from .cache import FileCache
    from .extract import ClaudeExtractor
    from .fetch import HttpxFetcher
    from .pipeline import extract_product

    cache = None if args.no_cache else FileCache(Path.home() / ".cache" / "styleid-charts")
    result = extract_product(
        args.url,
        fetcher=HttpxFetcher(),
        extractor=ClaudeExtractor(model=args.model),
        cache=cache,
        garment_kind=GarmentKind(args.kind),
    )
    if args.json:
        print(result.chart.model_dump_json(indent=2))
    else:
        print(format_text(result))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
