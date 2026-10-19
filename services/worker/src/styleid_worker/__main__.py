"""Run the queue worker: ``uv run python -m styleid_worker [--queues extraction] [--sweep DIR]``."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from styleid_api.jobs.worker import app

from .cleanup import sweep

SCAN_TTL_SECONDS = 24 * 3600


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="styleid_worker")
    ap.add_argument("--queues", default="extraction")
    ap.add_argument("--sweep", type=Path, help="scan upload root to sweep before starting")
    ap.add_argument("--sweep-only", action="store_true")
    ns = ap.parse_args(argv)
    if ns.sweep is not None:
        for p in sweep(ns.sweep, max_age_seconds=SCAN_TTL_SECONDS):
            print(f"removed stale upload {p}")
    if ns.sweep_only:
        return 0
    queues = [q.strip() for q in ns.queues.split(",") if q.strip()]

    async def run() -> None:
        async with app.open_async():
            await app.run_worker_async(queues=queues)

    asyncio.run(run())
    return 0


if __name__ == "__main__":
    sys.exit(main())
