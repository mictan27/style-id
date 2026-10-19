"""TTL caches for normalised charts keyed by the sha256 of the canonical URL."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from styleid_schema import NormalisedChart

from .fetch import canonicalise_url

DEFAULT_TTL_S = 30 * 24 * 3600
Clock = Callable[[], float]


def cache_key(url: str) -> str:
    """sha256 hex of the canonical URL."""
    return hashlib.sha256(canonicalise_url(url).encode("utf-8")).hexdigest()


class Cache(Protocol):
    """Get/set with a TTL in seconds."""

    def get(self, key: str) -> NormalisedChart | None:  # pragma: no cover - protocol
        ...

    def set(
        self, key: str, chart: NormalisedChart, *, ttl_s: float | None = None
    ) -> None:  # pragma: no cover - protocol
        ...


class MemoryCache:
    """Dict-backed cache. Inject `clock` to test expiry."""

    def __init__(self, *, ttl_s: float = DEFAULT_TTL_S, clock: Clock = time.time) -> None:
        self._ttl_s = ttl_s
        self._clock = clock
        self._items: dict[str, tuple[float, NormalisedChart]] = {}

    def get(self, key: str) -> NormalisedChart | None:
        """Return the chart if present and not expired."""
        item = self._items.get(key)
        if item is None:
            return None
        expires_at, chart = item
        if self._clock() >= expires_at:
            del self._items[key]
            return None
        return chart

    def set(self, key: str, chart: NormalisedChart, *, ttl_s: float | None = None) -> None:
        """Store the chart with the given or default TTL."""
        ttl = self._ttl_s if ttl_s is None else ttl_s
        self._items[key] = (self._clock() + ttl, chart)


class FileCache:
    """One JSON file per key under `directory`."""

    def __init__(
        self, directory: str | Path, *, ttl_s: float = DEFAULT_TTL_S, clock: Clock = time.time
    ) -> None:
        self._dir = Path(directory)
        self._ttl_s = ttl_s
        self._clock = clock
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        """File path for a key (keys are hex digests so they are safe filenames)."""
        safe = "".join(ch for ch in key if ch.isalnum() or ch in "-_")
        return self._dir / f"{safe}.json"

    def get(self, key: str) -> NormalisedChart | None:
        """Load the chart if the file exists and is not expired."""
        path = self._path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        if self._clock() >= float(payload.get("expires_at", 0)):
            path.unlink(missing_ok=True)
            return None
        return NormalisedChart.model_validate(payload["chart"])

    def set(self, key: str, chart: NormalisedChart, *, ttl_s: float | None = None) -> None:
        """Write the chart with its expiry time."""
        ttl = self._ttl_s if ttl_s is None else ttl_s
        payload = {
            "stored_at": self._clock(),
            "expires_at": self._clock() + ttl,
            "chart": chart.model_dump(mode="json"),
        }
        self._path(key).write_text(json.dumps(payload, indent=2), "utf-8")
