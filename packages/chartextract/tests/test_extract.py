from __future__ import annotations

import json
from pathlib import Path

import pytest
from chart_helpers import make_extraction

from styleid_charts import (
    Candidate,
    ClaudeExtractor,
    ExtractionResult,
    FakeExtractor,
    RecordingExtractor,
    content_hash,
    load_recorded,
)
from styleid_charts.extract import SYSTEM_PROMPT, render_candidates

CANDS = [
    Candidate("table", 10.0, "Size | Chest\nM | 52"),
    Candidate("image", 3.0, "https://x.example/chart.png"),
    Candidate("json_ld", 1.0, "name: Tee"),
]


def test_content_hash_is_stable_and_order_sensitive() -> None:
    assert content_hash(CANDS) == content_hash(list(CANDS))
    assert len(content_hash(CANDS)) == 16
    assert content_hash(CANDS) != content_hash(CANDS[::-1])


def test_fake_extractor_lookup_order() -> None:
    by_title = make_extraction([("M", [("Chest", 52)])])
    by_hash = make_extraction([("L", [("Chest", 56)])])
    default = make_extraction([], found=False)
    fake = FakeExtractor({"Tee": by_title, content_hash(CANDS): by_hash}, default=default)
    assert fake.extract(CANDS, page_title="Tee").extraction is by_title
    assert fake.extract(CANDS, page_title="Other").extraction is by_hash
    assert fake.extract(CANDS[:1], page_title=None).extraction is default
    assert fake.calls[0] == ("Tee", content_hash(CANDS))
    with pytest.raises(KeyError):
        FakeExtractor({}).extract(CANDS, page_title="nope")


def test_recording_extractor_writes_fixture(tmp_path: Path) -> None:
    ext = make_extraction([("M", [("Chest", 52)])])
    inner = FakeExtractor(default=ext, model_id="fake-1")
    rec = RecordingExtractor(inner, tmp_path)
    result = rec.extract(CANDS, page_title="Boxy Tee (Blue)")
    assert isinstance(result, ExtractionResult)
    path = tmp_path / "boxy-tee-blue.json"
    payload = json.loads(path.read_text())
    assert payload["model_id"] == "fake-1"
    assert payload["content_hash"] == content_hash(CANDS)
    assert load_recorded(path) == ext

    rec.extract(CANDS, page_title=None)
    assert (tmp_path / f"{content_hash(CANDS)}.json").exists()


def test_render_candidates_text_only_mentions_images() -> None:
    text = render_candidates(CANDS, page_title="Tee")
    assert text.startswith("Page title: Tee")
    assert "[candidate 1: table]" in text
    assert "[candidate 2: json_ld]" in text
    assert "https://x.example/chart.png" not in text
    assert "1 chart image(s) attached" in text


def test_claude_extractor_builds_messages_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHART_EXTRACTION_MODEL", "claude-test-model")
    extractor = ClaudeExtractor()
    assert extractor.model == "claude-test-model"
    messages = extractor.build_messages([CANDS[0], CANDS[2]], page_title="Tee")
    assert len(messages) == 1 and messages[0]["role"] == "user"
    content = messages[0]["content"]
    assert isinstance(content, list)
    assert len(content) == 1 and content[0]["type"] == "text"
    monkeypatch.delenv("CHART_EXTRACTION_MODEL")
    assert ClaudeExtractor().model == "claude-opus-5-5"
    assert ClaudeExtractor(model="x").model == "x"


def test_system_prompt_covers_the_rules() -> None:
    for phrase in (
        "body",
        "garment",
        "flat",
        "circumference",
        "midpoint",
        "verbatim",
        "center_back",
        "Do not invent",
    ):
        assert phrase in SYSTEM_PROMPT
