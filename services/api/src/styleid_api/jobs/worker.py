"""Entry point for the procrastinate worker::

uv run procrastinate --app styleid_api.jobs.worker.app worker --queues extraction
"""

from __future__ import annotations

from ..config import get_settings
from .extraction import make_procrastinate_app

_settings = get_settings()
app = make_procrastinate_app(_settings.database_url, _settings.chart_extraction_model)
