import os

from styleid_worker.cleanup import sweep


def test_sweep_removes_only_stale_dirs(tmp_path):
    old = tmp_path / "scan-old"
    old.mkdir()
    (old / "kf.jpg").write_bytes(b"x")
    fresh = tmp_path / "scan-fresh"
    fresh.mkdir()
    (fresh / "kf.jpg").write_bytes(b"x")
    (tmp_path / "loose-file").write_bytes(b"x")
    stale_time = 1_000_000.0
    os.utime(old / "kf.jpg", (stale_time, stale_time))
    removed = sweep(tmp_path, max_age_seconds=3600, now=stale_time + 7200)
    assert removed == [old]
    assert not old.exists() and fresh.exists()


def test_sweep_missing_root(tmp_path):
    assert sweep(tmp_path / "nope", max_age_seconds=1) == []
