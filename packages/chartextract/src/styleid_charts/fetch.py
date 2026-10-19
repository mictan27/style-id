"""Fetch a product page and expose its HTML plus the structured bits (JSON-LD, OpenGraph).

Two fetchers ship here: `HttpxFetcher` for static HTML and `PlaywrightFetcher` as an
optional rendered fallback. Tests inject `StaticFetcher`.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import httpx
from selectolax.lexbor import LexborHTMLParser

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)
TIMEOUT_S = 15.0

#: Query parameters that never identify a product variant.
_TRACKING_EXACT = frozenset(
    {
        "fbclid",
        "gclid",
        "dclid",
        "gbraid",
        "wbraid",
        "msclkid",
        "yclid",
        "igshid",
        "srsltid",
        "mc_cid",
        "mc_eid",
        "ref",
        "ref_",
        "referrer",
        "source",
        "campaign",
        "affiliate",
        "aff",
        "_ga",
        "_gl",
        "_hsenc",
        "_hsmi",
        "hsCtaTracking",
        "cmpid",
        "ncid",
        "spm",
    }
)
_TRACKING_PREFIXES = ("utm_", "pk_", "mtm_", "piwik_", "hsa_", "_bta_", "oly_")


def _is_tracking(key: str) -> bool:
    """True when a query parameter is an analytics/attribution parameter."""
    lower = key.lower()
    return lower in {k.lower() for k in _TRACKING_EXACT} or lower.startswith(_TRACKING_PREFIXES)


def canonicalise_url(url: str) -> str:
    """Normalise a product URL: lower-case host, no fragment, no tracking params, no trailing /."""
    parts = urlsplit(url.strip())
    scheme = (parts.scheme or "https").lower()
    netloc = parts.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parts.path.rstrip("/")
    kept = sorted(
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not _is_tracking(k)
    )
    query = urlencode(kept)
    return urlunsplit((scheme, netloc, path, query, ""))


@dataclass(frozen=True)
class FetchResult:
    """A fetched page with the structured data pulled out of it."""

    url: str
    final_url: str
    html: str
    status: int
    json_ld: list[dict[str, Any]] = field(default_factory=list)
    og: dict[str, str] = field(default_factory=dict)
    image_urls: list[str] = field(default_factory=list)
    rendered: bool = False


class Fetcher(Protocol):
    """Anything that turns a URL into a FetchResult."""

    def fetch(self, url: str) -> FetchResult:  # pragma: no cover - protocol
        ...


def _flatten_json_ld(node: Any, out: list[dict[str, Any]]) -> None:
    """Flatten lists and @graph wrappers into a list of plain JSON-LD nodes."""
    if isinstance(node, list):
        for item in node:
            _flatten_json_ld(item, out)
    elif isinstance(node, dict):
        graph = node.get("@graph")
        if isinstance(graph, list):
            _flatten_json_ld(graph, out)
        else:
            out.append(node)


def parse_json_ld(tree: LexborHTMLParser) -> list[dict[str, Any]]:
    """Return every JSON-LD node on the page, flattened."""
    out: list[dict[str, Any]] = []
    for script in tree.css('script[type="application/ld+json"]'):
        raw = script.text(strip=True)
        if not raw:
            continue
        try:
            _flatten_json_ld(json.loads(raw), out)
        except json.JSONDecodeError:
            continue
    return out


def parse_og(tree: LexborHTMLParser) -> dict[str, str]:
    """Return OpenGraph meta tags as {property-without-prefix: content}."""
    og: dict[str, str] = {}
    for meta in tree.css("meta[property^='og:']"):
        attrs = meta.attributes
        prop, content = attrs.get("property"), attrs.get("content")
        if prop and content:
            og[prop[3:]] = content
    return og


def parse_image_urls(tree: LexborHTMLParser, base_url: str) -> list[str]:
    """Return absolute image URLs found in <img> tags, in document order, de-duplicated."""
    seen: set[str] = set()
    urls: list[str] = []
    for img in tree.css("img"):
        src = img.attributes.get("src") or img.attributes.get("data-src")
        if not src or src.startswith("data:"):
            continue
        absolute = urljoin(base_url, src)
        if absolute not in seen:
            seen.add(absolute)
            urls.append(absolute)
    return urls


def is_product_node(node: dict[str, Any]) -> bool:
    """True when a JSON-LD node has @type Product (alone or in a list)."""
    kind = node.get("@type")
    kinds = kind if isinstance(kind, list) else [kind]
    return any(isinstance(k, str) and k.lower() == "product" for k in kinds)


def build_result(
    url: str, html: str, *, final_url: str | None = None, status: int = 200, rendered: bool = False
) -> FetchResult:
    """Parse HTML into a FetchResult (shared by every fetcher)."""
    final = final_url or url
    tree = LexborHTMLParser(html)
    return FetchResult(
        url=url,
        final_url=final,
        html=html,
        status=status,
        json_ld=parse_json_ld(tree),
        og=parse_og(tree),
        image_urls=parse_image_urls(tree, final),
        rendered=rendered,
    )


def has_chart_signal(result: FetchResult) -> bool:
    """True when the static HTML has a <table> or a JSON-LD Product (no render needed)."""
    return "<table" in result.html.lower() or any(is_product_node(n) for n in result.json_ld)


class StaticFetcher:
    """Fetcher that returns a fixed HTML string, for tests and the eval harness."""

    def __init__(self, html: str, *, status: int = 200, final_url: str | None = None) -> None:
        self._html = html
        self._status = status
        self._final_url = final_url

    def fetch(self, url: str) -> FetchResult:
        """Return the stored HTML as if fetched from `url`."""
        return build_result(url, self._html, final_url=self._final_url, status=self._status)


class HttpxFetcher:
    """Plain HTTP fetcher with a desktop UA, redirects and a 15 s timeout."""

    def __init__(self, *, timeout_s: float = TIMEOUT_S, client: httpx.Client | None = None) -> None:
        self._timeout_s = timeout_s
        self._client = client

    def fetch(self, url: str) -> FetchResult:
        """GET the page and parse it."""
        headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"}
        if self._client is not None:
            response = self._client.get(url, headers=headers, follow_redirects=True)
        else:
            with httpx.Client(timeout=self._timeout_s, follow_redirects=True) as client:
                response = client.get(url, headers=headers)
        return build_result(
            url, response.text, final_url=str(response.url), status=response.status_code
        )


class PlaywrightFetcher:
    """Rendered fetcher. Imports playwright lazily so the package works without a browser."""

    def __init__(self, *, timeout_s: float = TIMEOUT_S) -> None:
        self._timeout_ms = int(timeout_s * 1000)

    def fetch(self, url: str) -> FetchResult:
        """Render the page in headless Chromium and return the DOM after network idle."""
        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise RuntimeError(
                "PlaywrightFetcher needs the 'playwright' package: uv add playwright && "
                "uv run playwright install chromium"
            ) from exc
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                try:
                    page = browser.new_page(user_agent=USER_AGENT)
                    response = page.goto(url, wait_until="networkidle", timeout=self._timeout_ms)
                    html = page.content()
                    status = response.status if response is not None else 0
                    final_url = page.url
                finally:
                    browser.close()
        except PlaywrightError as exc:  # pragma: no cover - depends on environment
            raise RuntimeError(
                "Playwright could not launch Chromium; run 'uv run playwright install chromium'"
            ) from exc
        return build_result(url, html, final_url=final_url, status=status, rendered=True)


def fetch_with_fallback(url: str, *, fetchers: Sequence[Fetcher]) -> FetchResult:
    """Try fetchers in order; stop at the first page with a table or JSON-LD Product."""
    if not fetchers:
        raise ValueError("fetch_with_fallback needs at least one fetcher")
    result: FetchResult | None = None
    for fetcher in fetchers:
        result = fetcher.fetch(url)
        if has_chart_signal(result):
            return result
    assert result is not None
    return result
