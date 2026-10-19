from __future__ import annotations

import pytest

from styleid_charts import (
    FetchResult,
    StaticFetcher,
    canonicalise_url,
    fetch_with_fallback,
)
from styleid_charts.fetch import has_chart_signal


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://www.shop.example/p/tee/", "https://shop.example/p/tee"),
        ("https://Shop.Example/p/tee#reviews", "https://shop.example/p/tee"),
        (
            "https://shop.example/p/tee?utm_source=ig&utm_medium=social&fbclid=abc&gclid=1",
            "https://shop.example/p/tee",
        ),
        (
            "https://shop.example/p/tee?variant=42&utm_campaign=x",
            "https://shop.example/p/tee?variant=42",
        ),
        (
            "https://shop.example/p/tee?size=M&color=blue",
            "https://shop.example/p/tee?color=blue&size=M",
        ),
        (
            "https://shop.example/p/tee?ref=homepage&mc_cid=1&pk_campaign=a",
            "https://shop.example/p/tee",
        ),
        ("https://shop.example/", "https://shop.example"),
        ("  https://shop.example/p/tee?srsltid=zzz  ", "https://shop.example/p/tee"),
    ],
)
def test_canonicalise_url(raw: str, expected: str) -> None:
    assert canonicalise_url(raw) == expected


def test_canonicalise_is_idempotent() -> None:
    once = canonicalise_url("https://www.shop.example/p/tee/?variant=1&utm_x=2#frag")
    assert canonicalise_url(once) == once


def test_static_fetcher_parses_json_ld_og_and_images() -> None:
    html = (
        "<html><head><title>T</title>"
        '<meta property="og:title" content="Tee"><meta property="og:site_name" content="Shop">'
        '<script type="application/ld+json">'
        '{"@graph":[{"@type":"Product","name":"Tee"},{"@type":"Org"}]}</script>'
        '<script type="application/ld+json">not json</script>'
        '</head><body><img src="/a.jpg"><img src="data:image/png;base64,xx">'
        '<img src="/a.jpg"></body></html>'
    )
    result = StaticFetcher(html).fetch("https://shop.example/p")
    assert isinstance(result, FetchResult)
    assert result.og == {"title": "Tee", "site_name": "Shop"}
    assert [n.get("@type") for n in result.json_ld] == ["Product", "Org"]
    assert result.image_urls == ["https://shop.example/a.jpg"]
    assert result.rendered is False
    assert has_chart_signal(result)  # JSON-LD Product counts


def test_fetch_with_fallback_stops_at_first_signal() -> None:
    calls: list[str] = []

    class Recording(StaticFetcher):
        def __init__(self, name: str, html: str) -> None:
            super().__init__(html)
            self.name = name

        def fetch(self, url: str) -> FetchResult:
            calls.append(self.name)
            return super().fetch(url)

    plain = Recording("httpx", "<html><body><p>Loading...</p></body></html>")
    rendered = Recording(
        "playwright", "<html><body><table><tr><td>M</td></tr></table></body></html>"
    )

    result = fetch_with_fallback("https://x.example/p", fetchers=[plain, rendered])
    assert calls == ["httpx", "playwright"]
    assert "<table>" in result.html

    calls.clear()
    result = fetch_with_fallback("https://x.example/p", fetchers=[rendered, plain])
    assert calls == ["playwright"]


def test_fetch_with_fallback_returns_last_when_nothing_has_signal() -> None:
    a = StaticFetcher("<p>a</p>")
    b = StaticFetcher("<p>b</p>")
    assert fetch_with_fallback("https://x.example", fetchers=[a, b]).html == "<p>b</p>"
    with pytest.raises(ValueError):
        fetch_with_fallback("https://x.example", fetchers=[])
