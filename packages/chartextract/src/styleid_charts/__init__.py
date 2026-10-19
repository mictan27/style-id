"""styleid-charts: product URL -> normalised per-size garment measurements in cm."""

from .cache import DEFAULT_TTL_S, Cache, FileCache, MemoryCache, cache_key
from .candidates import Candidate, brand_hint, find_candidates, page_title
from .classify import classify, classify_unit
from .extract import (
    DEFAULT_MODEL,
    ClaudeExtractor,
    ExtractionError,
    ExtractionResult,
    Extractor,
    FakeExtractor,
    RecordingExtractor,
    content_hash,
    load_recorded,
)
from .fetch import (
    Fetcher,
    FetchResult,
    HttpxFetcher,
    PlaywrightFetcher,
    StaticFetcher,
    canonicalise_url,
    fetch_with_fallback,
)
from .normalise import (
    MEASURE_SYNONYMS,
    body_to_garment,
    map_measure,
    normalise,
    parse_value,
    stretch_class,
    to_cm,
)
from .pipeline import ProductExtraction, extract_product
from .sanity import SanityResult, check

__all__ = [
    "DEFAULT_MODEL",
    "DEFAULT_TTL_S",
    "MEASURE_SYNONYMS",
    "Cache",
    "Candidate",
    "ClaudeExtractor",
    "ExtractionError",
    "ExtractionResult",
    "Extractor",
    "FakeExtractor",
    "FetchResult",
    "Fetcher",
    "FileCache",
    "HttpxFetcher",
    "MemoryCache",
    "PlaywrightFetcher",
    "ProductExtraction",
    "RecordingExtractor",
    "SanityResult",
    "StaticFetcher",
    "body_to_garment",
    "brand_hint",
    "cache_key",
    "canonicalise_url",
    "check",
    "classify",
    "classify_unit",
    "content_hash",
    "extract_product",
    "fetch_with_fallback",
    "find_candidates",
    "load_recorded",
    "map_measure",
    "normalise",
    "page_title",
    "parse_value",
    "stretch_class",
    "to_cm",
]
