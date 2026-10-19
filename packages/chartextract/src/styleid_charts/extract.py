"""Ask Claude to read the candidates and return a ChartExtraction (structured output).

`ClaudeExtractor` is the real thing. `FakeExtractor` serves fixtures for offline tests, and
`RecordingExtractor` wraps a real extractor to capture those fixtures.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, cast

import httpx
from anthropic import Anthropic
from anthropic.types import ImageBlockParam, MessageParam, TextBlockParam

from styleid_schema import ChartExtraction

from .candidates import Candidate

DEFAULT_MODEL = "claude-opus-5-5"
MODEL_ENV = "CHART_EXTRACTION_MODEL"
MAX_IMAGES = 2
MAX_IMAGE_BYTES = 5 * 1024 * 1024
_IMAGE_TYPES = ("image/jpeg", "image/png", "image/gif", "image/webp")
ImageMediaType = Literal["image/jpeg", "image/png", "image/gif", "image/webp"]

SYSTEM_PROMPT = """You extract one clothing size chart from fragments of a product page.

You will receive the page title and up to five candidates: tables rendered as pipe-separated
rows, free text, a JSON-LD product record and sometimes images of a chart. Return exactly one
chart, following these rules:

1. Find the chart. If the page has no size chart at all set found=false with no rows. Pick the
   chart for the garment being sold (tops: tee, shirt, sweater, hoodie), not a generic
   footwear or bottoms chart.
2. Body vs garment. chart_kind="body" when the numbers describe the wearer ("fits chest
   96-100", "to fit bust", "your measurements"). chart_kind="garment" when they describe the
   garment itself ("pit to pit", "garment measurements", "laid flat"). Body chests for adults
   are roughly 80-130 cm (32-52 in); flat garment chest widths are roughly 40-70 cm.
3. Flat vs circumference. For garment charts, measure_basis="flat" when widths are across the
   garment lying flat (pit to pit, half chest); "circumference" when all the way around. Use
   "mixed" only when the page clearly mixes the two.
4. Units. Set unit to the chart's unit. If a cell states its own unit put it in the cell.
   Never convert units yourself; copy the numbers as printed.
5. Ranges. When a cell shows a range such as "96-100" or "38/40", put the midpoint (98, 39)
   as the value and mention it in notes.
6. Measure names. Copy each measure name verbatim from the page (for example "Chest (pit to
   pit)", "Length from HPS", "Sleeve from CB"). Do not rename or translate.
7. Length conventions. length_from="hps" when body length is from the high point of shoulder,
   "center_back" when from the centre back neck ("CB length"). sleeve_from="center_back" when
   sleeve is measured from the centre back neck, "shoulder_seam" when from the shoulder seam.
8. Sizes. One row per size exactly as labelled ("M", "40", "L/XL"). Do not invent sizes,
   rows or cells that are not on the page. Skip a size whose cells are all empty.
9. Fabric. Record fabric_composition verbatim if present, knit_or_woven if the page says or
   clearly implies it (jersey/tee = knit; poplin/oxford/twill = woven), and cut if stated.
10. Confidence. "high" when a clear table matched the garment, "medium" when you inferred
    kind or unit, "low" when the chart is partial, blurry or ambiguous.
"""


@dataclass(frozen=True)
class ExtractionResult:
    """The model's extraction plus what it cost."""

    extraction: ChartExtraction
    model_id: str
    input_tokens: int
    output_tokens: int


class Extractor(Protocol):
    """Turns candidates into a ChartExtraction."""

    def extract(
        self, candidates: Sequence[Candidate], *, page_title: str | None
    ) -> ExtractionResult:  # pragma: no cover - protocol
        ...


class ExtractionError(RuntimeError):
    """The model did not return a usable extraction."""


def content_hash(candidates: Sequence[Candidate]) -> str:
    """Stable short hash of the candidate contents, used as a fixture key."""
    digest = hashlib.sha256()
    for cand in candidates:
        digest.update(cand.kind.encode())
        digest.update(b"\0")
        digest.update(cand.content.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def render_candidates(candidates: Sequence[Candidate], *, page_title: str | None) -> str:
    """Render the text candidates as the user message body."""
    parts = [f"Page title: {page_title or 'unknown'}"]
    for i, cand in enumerate(c for c in candidates if c.kind != "image"):
        parts.append(f"[candidate {i + 1}: {cand.kind}]\n{cand.content}")
    images = [c for c in candidates if c.kind == "image"]
    if images:
        parts.append(f"[{min(len(images), MAX_IMAGES)} chart image(s) attached]")
    return "\n\n".join(parts)


def _model_from_env() -> str:
    """Model id from CHART_EXTRACTION_MODEL, else the default."""
    return os.environ.get(MODEL_ENV, "").strip() or DEFAULT_MODEL


def fetch_image_block(url: str, client: httpx.Client) -> ImageBlockParam | None:
    """Download an image and wrap it as a base64 image block; None if not a usable image."""
    try:
        response = client.get(url, follow_redirects=True)
    except httpx.HTTPError:
        return None
    media_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
    if response.status_code != 200 or media_type not in _IMAGE_TYPES:
        return None
    if len(response.content) > MAX_IMAGE_BYTES:
        return None
    data = base64.standard_b64encode(response.content).decode("ascii")
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": cast(ImageMediaType, media_type),
            "data": data,
        },
    }


class ClaudeExtractor:
    """Structured-output extraction with the Anthropic SDK (`messages.parse`)."""

    def __init__(
        self,
        *,
        client: Anthropic | None = None,
        model: str | None = None,
        http_client: httpx.Client | None = None,
        max_tokens: int = 8192,
    ) -> None:
        self._client = client
        self._model = model or _model_from_env()
        self._http_client = http_client
        self._max_tokens = max_tokens

    @property
    def model(self) -> str:
        """Model id used for extraction."""
        return self._model

    def _anthropic(self) -> Anthropic:
        """Lazily build the client so importing the module never needs a key."""
        if self._client is None:
            self._client = Anthropic()
        return self._client

    def build_messages(
        self, candidates: Sequence[Candidate], *, page_title: str | None
    ) -> list[MessageParam]:
        """Build the user message: text candidates plus up to two chart images."""
        blocks: list[TextBlockParam | ImageBlockParam] = []
        images = [c for c in candidates if c.kind == "image"][:MAX_IMAGES]
        if images:
            http = self._http_client or httpx.Client(timeout=15.0)
            try:
                for image in images:
                    block = fetch_image_block(image.content, http)
                    if block is not None:
                        blocks.append(block)
            finally:
                if self._http_client is None:
                    http.close()
        blocks.append(
            {"type": "text", "text": render_candidates(candidates, page_title=page_title)}
        )
        return [{"role": "user", "content": blocks}]

    def extract(
        self, candidates: Sequence[Candidate], *, page_title: str | None
    ) -> ExtractionResult:
        """Call Claude once and return the parsed ChartExtraction with token usage."""
        response = self._anthropic().messages.parse(
            model=self._model,
            max_tokens=self._max_tokens,
            system=[
                {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}
            ],
            messages=self.build_messages(candidates, page_title=page_title),
            output_format=ChartExtraction,
        )
        if response.stop_reason == "refusal":
            raise ExtractionError("model refused the extraction request")
        parsed = response.parsed_output
        if parsed is None:
            raise ExtractionError(f"no structured output (stop_reason={response.stop_reason})")
        usage = response.usage
        input_tokens = (
            usage.input_tokens
            + (usage.cache_creation_input_tokens or 0)
            + (usage.cache_read_input_tokens or 0)
        )
        return ExtractionResult(
            extraction=parsed,
            model_id=response.model,
            input_tokens=input_tokens,
            output_tokens=usage.output_tokens,
        )


class FakeExtractor:
    """Serve fixtures keyed by page title or by `content_hash(candidates)`."""

    def __init__(
        self,
        fixtures: dict[str, ChartExtraction] | None = None,
        *,
        default: ChartExtraction | None = None,
        model_id: str = "fake",
    ) -> None:
        self._fixtures = dict(fixtures or {})
        self._default = default
        self._model_id = model_id
        self.calls: list[tuple[str | None, str]] = []

    def extract(
        self, candidates: Sequence[Candidate], *, page_title: str | None
    ) -> ExtractionResult:
        """Look up by title, then by content hash, then the default; KeyError otherwise."""
        key = content_hash(candidates)
        self.calls.append((page_title, key))
        extraction = None
        if page_title is not None:
            extraction = self._fixtures.get(page_title)
        if extraction is None:
            extraction = self._fixtures.get(key, self._default)
        if extraction is None:
            raise KeyError(f"no fixture for title={page_title!r} or hash={key}")
        return ExtractionResult(extraction, self._model_id, 0, 0)


def _slug(text: str) -> str:
    """Filesystem-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "page"


class RecordingExtractor:
    """Wrap an extractor and write each response to `directory/<slug>.json`."""

    def __init__(self, inner: Extractor, directory: str | Path) -> None:
        self._inner = inner
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)

    def extract(
        self, candidates: Sequence[Candidate], *, page_title: str | None
    ) -> ExtractionResult:
        """Delegate, then persist the result as a fixture."""
        result = self._inner.extract(candidates, page_title=page_title)
        key = content_hash(candidates)
        payload = {
            "page_title": page_title,
            "content_hash": key,
            "model_id": result.model_id,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "extraction": result.extraction.model_dump(mode="json"),
        }
        name = _slug(page_title) if page_title else key
        (self._dir / f"{name}.json").write_text(json.dumps(payload, indent=2), "utf-8")
        return result


def load_recorded(path: str | Path) -> ChartExtraction:
    """Read a fixture written by RecordingExtractor (or a bare ChartExtraction JSON)."""
    payload = json.loads(Path(path).read_text("utf-8"))
    data = payload.get("extraction", payload)
    return ChartExtraction.model_validate(data)
