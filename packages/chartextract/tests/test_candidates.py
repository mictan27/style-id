from __future__ import annotations

from chart_helpers import load_page

from styleid_charts import StaticFetcher, brand_hint, find_candidates, page_title
from styleid_charts.candidates import score_text, serialise_table

NAV_PAGE = """<html><head><title>Boxy Tee | Shop</title></head><body>
<nav><table><tr><th>Store</th><th>Hours</th></tr><tr><td>Soho</td><td>9-5</td></tr></table></nav>
<main>
<table id="shipping"><tr><th>Zone</th><th>Price</th></tr>
<tr><td>EU</td><td>9.00</td></tr><tr><td>US</td><td>12.00</td></tr></table>
<h2>Size chart</h2>
<table id="sizes"><tr><th>Size</th><th>Chest</th><th>Length</th></tr>
<tr><td>S</td><td>50</td><td>68</td></tr><tr><td>M</td><td>53</td><td>70</td></tr></table>
<img src="/img/size-guide.png" alt="size guide">
<img src="/img/front.jpg" alt="front view">
</main>
<footer><table><tr><td>Contact</td><td>hello@shop.example</td></tr></table></footer>
<script>var x = "chest length sleeve 50 60 70";</script>
</body></html>"""


def test_size_table_ranks_first_and_boilerplate_is_dropped() -> None:
    fetch = StaticFetcher(NAV_PAGE).fetch("https://shop.example/p/boxy-tee")
    cands = find_candidates(fetch)
    assert cands[0].kind == "table"
    assert cands[0].content.startswith("Size | Chest | Length")
    assert "S | 50 | 68" in cands[0].content
    contents = "\n".join(c.content for c in cands)
    assert "Soho" not in contents  # nav table removed
    assert "hello@shop.example" not in contents  # footer removed
    assert "var x" not in contents  # script removed
    assert len(cands) <= 5


def test_image_candidates_only_when_hinted() -> None:
    fetch = StaticFetcher(NAV_PAGE).fetch("https://shop.example/p/boxy-tee")
    images = [c for c in find_candidates(fetch) if c.kind == "image"]
    assert [c.content for c in images] == ["https://shop.example/img/size-guide.png"]


def test_scores_prefer_measurement_rich_text() -> None:
    assert score_text("Zone | Price\nEU | 9.00") == 0.0
    assert score_text("Size | Chest | Length\nS | 50 | 68\nM | 53 | 70") > 5


def test_serialise_table_pipes() -> None:
    fetch = StaticFetcher(NAV_PAGE).fetch("https://shop.example")
    from selectolax.lexbor import LexborHTMLParser

    table = LexborHTMLParser(fetch.html).css_first("#sizes")
    assert table is not None
    assert serialise_table(table).splitlines() == [
        "Size | Chest | Length",
        "S | 50 | 68",
        "M | 53 | 70",
    ]


def test_dl_and_heading_candidates() -> None:
    html, _, _ = load_page("fjord_dl_ranges")
    fetch = StaticFetcher(html).fetch("https://fjordwear.example/products/linen-camp-shirt")
    cands = find_candidates(fetch)
    assert cands and all(c.kind == "text" for c in cands)
    assert any("S (to fit): Chest 88" in c.content for c in cands)


def test_json_ld_candidate_when_no_chart() -> None:
    html, _, _ = load_page("linden_shop_jsonld_only")
    fetch = StaticFetcher(html).fetch("https://shop.linden.example/item/9981-linen-shirt")
    cands = find_candidates(fetch)
    assert [c.kind for c in cands] == ["json_ld"]
    assert "brand: Linden" in cands[0].content


def test_page_title_and_brand_hint_fallbacks() -> None:
    html, _, _ = load_page("acme_tee_flat_cm")
    fetch = StaticFetcher(html).fetch("https://www.acme-apparel.example/p")
    assert page_title(fetch) == "Heavyweight Tee"
    assert brand_hint(fetch) == "Acme Apparel"

    bare = StaticFetcher("<html><head><title>Only Title</title></head><body></body></html>")
    fetch = bare.fetch("https://www.plain-store.example/x")
    assert page_title(fetch) == "Only Title"
    assert brand_hint(fetch) == "plain-store.example"

    fetch = StaticFetcher("<html><body><h1>From H1</h1></body></html>").fetch("https://h.example")
    assert page_title(fetch) == "From H1"
    assert find_candidates(fetch) == []
