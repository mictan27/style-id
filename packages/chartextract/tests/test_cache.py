from __future__ import annotations

from pathlib import Path

from chart_helpers import make_extraction

from styleid_charts import DEFAULT_TTL_S, FileCache, MemoryCache, cache_key, normalise


class FakeClock:
    def __init__(self, now: float = 1_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def test_cache_key_is_canonical_sha256() -> None:
    a = cache_key("https://www.shop.example/p/tee/?utm_source=x")
    b = cache_key("https://shop.example/p/tee")
    assert a == b
    assert len(a) == 64
    assert cache_key("https://shop.example/p/other") != a


def test_memory_cache_ttl_expiry() -> None:
    clock = FakeClock()
    cache = MemoryCache(ttl_s=100, clock=clock)
    chart = normalise(make_extraction([("M", [("Chest", 52)])]))
    assert cache.get("k") is None
    cache.set("k", chart)
    assert cache.get("k") == chart
    clock.now += 99
    assert cache.get("k") == chart
    clock.now += 1
    assert cache.get("k") is None


def test_memory_cache_per_item_ttl() -> None:
    clock = FakeClock()
    cache = MemoryCache(clock=clock)
    chart = normalise(make_extraction([("M", [("Chest", 52)])]))
    cache.set("k", chart, ttl_s=5)
    clock.now += 6
    assert cache.get("k") is None


def test_file_cache_round_trip_and_expiry(tmp_path: Path) -> None:
    clock = FakeClock()
    cache = FileCache(tmp_path / "charts", clock=clock)
    chart = normalise(make_extraction([("M", [("Chest", 52), ("CB Length", 68)])]))
    key = cache_key("https://shop.example/p")
    cache.set(key, chart)
    assert (tmp_path / "charts" / f"{key}.json").exists()
    assert FileCache(tmp_path / "charts", clock=clock).get(key) == chart
    clock.now += DEFAULT_TTL_S
    assert cache.get(key) is None
    assert not (tmp_path / "charts" / f"{key}.json").exists()


def test_file_cache_ignores_corrupt_files(tmp_path: Path) -> None:
    cache = FileCache(tmp_path)
    (tmp_path / "bad.json").write_text("{not json")
    assert cache.get("bad") is None
    assert cache.get("missing") is None
