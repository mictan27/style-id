"""fetch -> candidates -> extract -> classify -> normalise -> sanity -> cache."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from styleid_schema import (
    ChartClassification,
    ChartStatus,
    GarmentKind,
    NormalisedChart,
    Zone,
)

from .cache import Cache, cache_key
from .candidates import brand_hint, find_candidates, page_title
from .classify import classify
from .extract import Extractor
from .fetch import Fetcher, canonicalise_url
from .normalise import normalise


@dataclass(frozen=True)
class ProductExtraction:
    """Everything the pipeline learned about one product URL."""

    url: str
    canonical_url: str
    title: str | None
    brand_hint: str | None
    chart: NormalisedChart
    tokens_in: int = 0
    tokens_out: int = 0
    from_cache: bool = False


_UNKNOWN = ChartClassification(chart_kind="unknown", measure_basis="unknown", unit="unknown")


def extract_product(
    url: str,
    *,
    fetcher: Fetcher,
    extractor: Extractor,
    cache: Cache | None = None,
    garment_kind: GarmentKind = GarmentKind.TEE,
    typical_ease: Mapping[Zone, float] | None = None,
) -> ProductExtraction:
    """Run the whole pipeline for one product URL, using the cache when it has a fresh entry."""
    canonical = canonicalise_url(url)
    key = cache_key(canonical)
    if cache is not None and (cached := cache.get(key)) is not None:
        return ProductExtraction(url, canonical, None, None, cached, from_cache=True)

    fetched = fetcher.fetch(url)
    title = page_title(fetched)
    brand = brand_hint(fetched)
    candidates = find_candidates(fetched)
    if not candidates:
        chart = NormalisedChart(
            status=ChartStatus.NOT_FOUND,
            classification=_UNKNOWN,
            warnings=["no size-chart candidates on the page"],
        )
        return ProductExtraction(url, canonical, title, brand, chart)

    result = extractor.extract(candidates, page_title=title)
    page_text = "\n".join(c.content for c in candidates if c.kind != "image")
    classification = classify(result.extraction, page_text=page_text)
    chart = normalise(
        result.extraction,
        garment_kind=garment_kind,
        typical_ease=typical_ease,
        classification=classification,
        model_id=result.model_id,
    )
    if cache is not None and chart.status is not ChartStatus.FAILED:
        cache.set(key, chart)
    return ProductExtraction(
        url=url,
        canonical_url=canonical,
        title=title,
        brand_hint=brand,
        chart=chart,
        tokens_in=result.input_tokens,
        tokens_out=result.output_tokens,
    )
