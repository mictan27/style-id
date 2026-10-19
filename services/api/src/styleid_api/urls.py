"""Product URL canonicalisation.

Two shoppers sharing the same product with different tracking parameters must land
on the same ``products`` row, so the canonical URL is the lookup key.

``canonicalise_url`` applies ``styleid_charts.fetch.canonicalise_url`` (the fetcher's
notion of identity) when that package is importable, then folds scheme and default
port on top so ``http://www.shop.example.com:80/x`` and ``https://shop.example.com/x``
are one product. Without the package only the local rules run.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_PREFIXES = ("utm_", "mc_", "pk_", "piwik_", "hsa_", "vero_")
_TRACKING_PARAMS = frozenset(
    {
        "fbclid",
        "gclid",
        "gclsrc",
        "dclid",
        "msclkid",
        "ttclid",
        "igshid",
        "yclid",
        "twclid",
        "ref",
        "ref_",
        "referrer",
        "affiliate",
        "aff",
        "afftrack",
        "cjevent",
        "irclickid",
        "srsltid",
        "_ga",
        "_gl",
        "mkt_tok",
        "spm",
        "scm",
        "s_kwcid",
        "ef_id",
    }
)
_DEFAULT_PORTS = {"http": "80", "https": "443"}


def _is_tracking(name: str) -> bool:
    lowered = name.lower()
    return lowered in _TRACKING_PARAMS or lowered.startswith(_TRACKING_PREFIXES)


def canonicalise_url_local(url: str) -> str:
    """Force https, lower-case the host, drop default ports, fragments, tracking parameters and
    a trailing slash; sort the surviving query parameters."""
    raw = url.strip()
    if "://" not in raw:
        raw = "https://" + raw
    parts = urlsplit(raw)
    # http and https are the same product; shops redirect to https anyway.
    original_scheme = parts.scheme.lower() or "https"
    scheme = "https" if original_scheme in ("http", "https") else original_scheme
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    port = parts.port
    netloc = host
    if port is not None and str(port) not in (
        _DEFAULT_PORTS.get(original_scheme),
        _DEFAULT_PORTS["https"],
    ):
        netloc = f"{host}:{port}"
    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    query_pairs = [
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not _is_tracking(k)
    ]
    query = urlencode(sorted(query_pairs), doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def _load_charts_canonicaliser() -> Callable[[str], str] | None:
    try:
        module = importlib.import_module("styleid_charts.fetch")
    except ImportError:
        return None
    fn = getattr(module, "canonicalise_url", None)
    return fn if callable(fn) else None


def canonicalise_url(url: str) -> str:
    """The chart-extraction package's canonicaliser first (so the fetcher and the API agree
    on identity), then the local scheme/port folding. Local rules alone if it is absent."""
    fn = _load_charts_canonicaliser()
    if fn is not None:
        result = fn(url)
        if isinstance(result, str) and result:
            url = result
    return canonicalise_url_local(url)


def domain_of(canonical_url: str) -> str:
    return urlsplit(canonical_url).hostname or ""
