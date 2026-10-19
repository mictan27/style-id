from __future__ import annotations

import pytest
from chart_helpers import load_page

from styleid_charts import (
    FakeExtractor,
    ProductExtraction,
    StaticFetcher,
    extract_product,
    load_recorded,
)
from styleid_charts.__main__ import build_parser, format_text, main


def test_parser_defaults() -> None:
    args = build_parser().parse_args(["https://shop.example/p"])
    assert args.url == "https://shop.example/p"
    assert args.kind == "tee"
    assert args.json is False
    assert args.model is None
    assert args.no_cache is False


def test_parser_options() -> None:
    args = build_parser().parse_args(
        ["https://x", "--kind", "shirt", "--json", "--model", "m", "--no-cache"]
    )
    assert (args.kind, args.json, args.model, args.no_cache) == ("shirt", True, "m", True)


def test_parser_rejects_bad_kind_and_missing_url() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["https://x", "--kind", "trousers"])
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_format_text_renders_sizes_and_flags() -> None:
    html, expected, folder = load_page("harbor_knit_circ_cb")
    result = extract_product(
        expected["url"],
        fetcher=StaticFetcher(html),
        extractor=FakeExtractor(default=load_recorded(folder / "extraction.json")),
    )
    text = format_text(result)
    assert "status:  ok" in text
    assert "M: chest_width=50" in text
    assert "length from CB; sleeve from CB" in text
    assert "tokens:  in=0 out=0" in text
    cached = ProductExtraction(
        result.url, result.canonical_url, None, None, result.chart, from_cache=True
    )
    assert "(cached)" in format_text(cached)


def test_main_wires_fetcher_and_extractor(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    html, expected, folder = load_page("acme_tee_flat_cm")
    monkeypatch.setattr("styleid_charts.fetch.HttpxFetcher", lambda: StaticFetcher(html))
    monkeypatch.setattr(
        "styleid_charts.extract.ClaudeExtractor",
        lambda model=None: FakeExtractor(default=load_recorded(folder / "extraction.json")),
    )
    assert main([expected["url"], "--json", "--no-cache"]) == 0
    out = capsys.readouterr().out
    assert '"status": "ok"' in out
    assert '"chest_width"' in out
