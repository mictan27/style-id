"""Delete raw scan uploads older than a TTL. Backstop for the worker's own deletion."""

from __future__ import annotations

import shutil
import time
from pathlib import Path


def sweep(upload_root: Path, *, max_age_seconds: float, now: float | None = None) -> list[Path]:
    """Remove upload directories whose newest file is older than max_age_seconds."""
    now = time.time() if now is None else now
    removed: list[Path] = []
    if not upload_root.is_dir():
        return removed
    for entry in sorted(upload_root.iterdir()):
        if not entry.is_dir():
            continue
        files = [p for p in entry.rglob("*") if p.is_file()]
        newest = max((p.stat().st_mtime for p in files), default=entry.stat().st_mtime)
        if now - newest > max_age_seconds:
            shutil.rmtree(entry, ignore_errors=True)
            removed.append(entry)
    return removed
