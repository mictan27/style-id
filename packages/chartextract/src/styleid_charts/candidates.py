"""Find the parts of a product page that might be a size chart and rank them.

Candidates are compact text (tables, definition lists, text under a "size guide" heading),
image URLs that look like chart images, and the JSON-LD Product node.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urljoin, urlsplit

from selectolax.lexbor import LexborHTMLParser, LexborNode

from .fetch import FetchResult, is_product_node

CandidateKind = Literal["table", "text", "image", "json_ld"]

MAX_CANDIDATES = 5
MAX_TEXT_CHARS = 4000
_BOILERPLATE = ("nav", "footer", "script", "style", "noscript", "svg", "iframe", "template")

_SIZE_WORD = re.compile(
    r"(?<![a-z0-9])(xxs|xs|s|m|l|xl|xxl|xxxl|2xl|3xl|4xl|one size|"
    r"small|medium|large|size)(?![a-z0-9])",
    re.IGNORECASE,
)
_SIZE_NUMBER = re.compile(r"(?<![\d.])(3[0-9]|4[0-9]|5[0-9]|6[0-4])(?![\d.])")
_MEASURE_WORD = re.compile(
    r"(?<![a-z])(chest|bust|pit|length|shoulder|sleeve|hem|waist|collar|neck|bicep|"
    r"cm|in|inch|inches|width|measurements?)(?![a-z])|\"",
    re.IGNORECASE,
)
_GUIDE_HEADING = re.compile(
    r"size\s*(guide|chart|table|info)|measurements?|fit\s*guide|sizing", re.IGNORECASE
)
_IMAGE_HINT = re.compile(r"size|chart|guide|measure|sizing", re.IGNORECASE)
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_CAPTION_TAGS = frozenset(
    {"figure", "figcaption", "a", "picture", "span", "p", "button", "summary", "li", "label"}
)


@dataclass(frozen=True)
class Candidate:
    """One chunk of page content that may contain the size chart."""

    kind: CandidateKind
    score: float
    content: str


def _clean(text: str) -> str:
    """Collapse whitespace."""
    return re.sub(r"\s+", " ", text).strip()


def score_text(text: str) -> float:
    """Score text by size words, measurement words and the amount of numbers it carries."""
    size_hits = len(_SIZE_WORD.findall(text)) + min(len(_SIZE_NUMBER.findall(text)), 8)
    measure_hits = len(set(m.lower() for m in _MEASURE_WORD.findall(text) if m)) + text.count('"')
    numbers = min(len(_NUMBER.findall(text)), 40)
    if measure_hits == 0:
        return 0.0
    return min(size_hits, 12) * 1.0 + measure_hits * 2.0 + numbers * 0.25


def _strip_boilerplate(tree: LexborHTMLParser) -> None:
    """Remove nav/footer/script/style blocks so they cannot become candidates."""
    for tag in _BOILERPLATE:
        for node in tree.css(tag):
            node.decompose()


def _heading_bonus(node: LexborNode) -> float:
    """Bonus when a nearby preceding heading or caption talks about sizing."""
    caption = node.css_first("caption")
    if caption is not None and _GUIDE_HEADING.search(caption.text()):
        return 6.0
    cursor: LexborNode | None = node
    for _ in range(4):
        if cursor is None:
            break
        prev = cursor.prev
        while prev is not None and (prev.tag is None or prev.tag in ("-text", "_text")):
            prev = prev.prev
        if prev is not None and _GUIDE_HEADING.search(_clean(prev.text())):
            return 6.0
        cursor = cursor.parent
    return 0.0


def serialise_table(table: LexborNode) -> str:
    """Render a <table> as pipe-separated rows (one line per row)."""
    lines: list[str] = []
    for row in table.css("tr"):
        cells = [_clean(c.text()) for c in row.css("th, td")]
        if any(cells):
            lines.append(" | ".join(cells))
    return "\n".join(lines)


def serialise_dl(dl: LexborNode) -> str:
    """Render a <dl> as 'term: definition' lines."""
    lines: list[str] = []
    term: str | None = None
    for child in dl.iter():
        if child.tag == "dt":
            term = _clean(child.text())
        elif child.tag == "dd":
            definition = _clean(child.text())
            lines.append(f"{term}: {definition}" if term else definition)
    return "\n".join(lines)


def _text_after_heading(heading: LexborNode) -> str:
    """Collect the text of the siblings following a heading, up to a cap."""
    parts: list[str] = []
    total = 0
    sibling = heading.next
    while sibling is not None and total < MAX_TEXT_CHARS // 2:
        if sibling.tag and sibling.tag.startswith("h") and len(sibling.tag) == 2:
            break
        text = _clean(sibling.text(separator=" "))
        if text:
            parts.append(text)
            total += len(text)
        sibling = sibling.next
    return "\n".join(parts)


def _table_candidates(tree: LexborHTMLParser) -> list[Candidate]:
    """Score every table on the page."""
    out: list[Candidate] = []
    for table in tree.css("table"):
        content = serialise_table(table)
        if not content:
            continue
        score = score_text(content)
        if score <= 0:
            continue
        out.append(
            Candidate("table", score + 2.0 + _heading_bonus(table), content[:MAX_TEXT_CHARS])
        )
    return out


def _list_candidates(tree: LexborHTMLParser) -> list[Candidate]:
    """Score <dl> and <ul> blocks that mention measurements."""
    out: list[Candidate] = []
    for dl in tree.css("dl"):
        content = serialise_dl(dl)
        score = score_text(content)
        if score > 0:
            out.append(Candidate("text", score + _heading_bonus(dl), content[:MAX_TEXT_CHARS]))
    for ul in tree.css("ul, ol"):
        items = [_clean(li.text()) for li in ul.css("li")]
        content = "\n".join(i for i in items if i)
        score = score_text(content)
        if score > 0 and len(_NUMBER.findall(content)) >= 2:
            out.append(Candidate("text", score + _heading_bonus(ul), content[:MAX_TEXT_CHARS]))
    return out


def _heading_candidates(tree: LexborHTMLParser) -> list[Candidate]:
    """Text sitting under a 'size guide'-like heading."""
    out: list[Candidate] = []
    for heading in tree.css("h1, h2, h3, h4, h5, h6, summary, strong, b"):
        if not _GUIDE_HEADING.search(_clean(heading.text())):
            continue
        content = _text_after_heading(heading)
        score = score_text(content)
        if score > 0 and len(_NUMBER.findall(content)) >= 2:
            out.append(Candidate("text", score + 3.0, content[:MAX_TEXT_CHARS]))
    return out


def _image_candidates(tree: LexborHTMLParser, base_url: str) -> list[Candidate]:
    """Images whose src/alt/title or surrounding text hints at a size chart."""
    out: list[Candidate] = []
    for img in tree.css("img"):
        attrs = img.attributes
        src = attrs.get("src") or attrs.get("data-src")
        if not src or src.startswith("data:"):
            continue
        hint_text = " ".join(filter(None, (src, attrs.get("alt"), attrs.get("title"))))
        parent = img.parent
        if parent is not None and parent.tag in _CAPTION_TAGS and parent.css_first("table") is None:
            nearby = _clean(parent.text(separator=" "))
            if len(nearby) <= 200:  # a caption or link label, not the whole page
                hint_text += " " + nearby
        hits = len(set(h.lower() for h in _IMAGE_HINT.findall(hint_text)))
        if hits == 0:
            continue
        out.append(Candidate("image", 2.0 + hits * 1.5, urljoin(base_url, src)))
    return out


def _json_ld_candidate(fetch: FetchResult) -> Candidate | None:
    """Compact description of the JSON-LD Product node, if present."""
    for node in fetch.json_ld:
        if not is_product_node(node):
            continue
        brand = node.get("brand")
        brand_name = brand.get("name") if isinstance(brand, dict) else brand
        offers = node.get("offers")
        offer_text = ""
        if isinstance(offers, dict):
            offer_text = f"{offers.get('price', '')} {offers.get('priceCurrency', '')}".strip()
        description = str(node.get("description") or "")[:800]
        fields = {
            "name": node.get("name"),
            "brand": brand_name,
            "material": node.get("material"),
            "description": description,
            "offers": offer_text,
        }
        content = "\n".join(f"{k}: {v}" for k, v in fields.items() if v)
        return Candidate("json_ld", 1.0 + score_text(content), content)
    return None


def find_candidates(fetch: FetchResult, *, limit: int = MAX_CANDIDATES) -> list[Candidate]:
    """Return the top candidates for `fetch`, highest score first."""
    tree = LexborHTMLParser(fetch.html)
    _strip_boilerplate(tree)
    found: list[Candidate] = []
    found.extend(_table_candidates(tree))
    found.extend(_list_candidates(tree))
    found.extend(_heading_candidates(tree))
    found.extend(_image_candidates(tree, fetch.final_url))
    json_ld = _json_ld_candidate(fetch)
    if json_ld is not None:
        found.append(json_ld)
    seen: set[str] = set()
    unique: list[Candidate] = []
    for cand in sorted(found, key=lambda c: c.score, reverse=True):
        if cand.content in seen:
            continue
        seen.add(cand.content)
        unique.append(cand)
    return unique[:limit]


def _product_node(fetch: FetchResult) -> dict[str, Any] | None:
    """First JSON-LD Product node, if any."""
    return next((n for n in fetch.json_ld if is_product_node(n)), None)


def page_title(fetch: FetchResult) -> str | None:
    """Best available product title: og:title, JSON-LD name, <title>, then <h1>."""
    if title := fetch.og.get("title"):
        return _clean(title)
    product = _product_node(fetch)
    if product is not None and isinstance(product.get("name"), str):
        return _clean(product["name"])
    tree = LexborHTMLParser(fetch.html)
    for selector in ("title", "h1"):
        node = tree.css_first(selector)
        if node is not None and _clean(node.text()):
            return _clean(node.text())
    return None


def brand_hint(fetch: FetchResult) -> str | None:
    """Brand from JSON-LD, else og:site_name, else the page's domain."""
    product = _product_node(fetch)
    if product is not None:
        brand = product.get("brand")
        if isinstance(brand, dict) and isinstance(brand.get("name"), str):
            return _clean(brand["name"])
        if isinstance(brand, str) and brand.strip():
            return _clean(brand)
    if site := fetch.og.get("site_name"):
        return _clean(site)
    host = urlsplit(fetch.final_url or fetch.url).netloc.lower()
    host = host.removeprefix("www.")
    return host or None
