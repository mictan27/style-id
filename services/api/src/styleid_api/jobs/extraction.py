"""The extraction seam between the API and ``styleid_charts``.

``ExtractFn`` is the only contract: ``(url, garment_kind) -> NormalisedChart``.
``process_size_chart`` turns one ``size_charts`` row from ``pending`` into a final
state and, on ``ok``, materialises one catalogue ``garments`` row per size.

Runners decide *where* that happens:

* ``InlineRunner`` runs it synchronously inside the request (dev, tests).
* ``QueueRunner`` defers a procrastinate job on the Postgres queue; the worker runs
  the same ``process_size_chart``.
"""

from __future__ import annotations

import importlib
import logging
from collections.abc import Callable
from typing import Any, Protocol

import procrastinate
from sqlalchemy import delete

from styleid_schema import ChartStatus, GarmentKind, NormalisedChart

from ..db.models import Garment, Product, SizeChart, SizeChartStatus, utcnow
from ..db.session import SessionFactory, make_engine, make_session_factory

log = logging.getLogger(__name__)

ExtractFn = Callable[[str, GarmentKind], NormalisedChart]

TASK_NAME = "styleid_api.jobs.extraction.extract_size_chart"
QUEUE_NAME = "extraction"


class ExtractionUnavailable(RuntimeError):
    """``styleid_charts`` is missing or does not expose ``pipeline.extract_product`` yet."""


class ExtractionRunner(Protocol):
    def run(self, size_chart_id: str) -> None: ...


def make_default_extract(model: str | None = None) -> ExtractFn:
    """Production implementation: ``styleid_charts.extract_product`` with an ``HttpxFetcher``
    and a ``ClaudeExtractor`` for ``model`` (``CHART_EXTRACTION_MODEL`` when ``None``).

    ``styleid_charts`` is imported lazily and reached through ``getattr`` so the API imports
    and serves everything else while that package evolves; a missing or mismatched module
    becomes a ``failed`` chart with a clear ``error`` instead of a crashed process."""

    def extract(url: str, garment_kind: GarmentKind) -> NormalisedChart:
        try:
            charts = importlib.import_module("styleid_charts")
        except ImportError as exc:
            raise ExtractionUnavailable(f"styleid_charts is not importable: {exc}") from exc
        extract_product = getattr(charts, "extract_product", None)
        fetcher_cls = getattr(charts, "HttpxFetcher", None)
        extractor_cls = getattr(charts, "ClaudeExtractor", None)
        if not all(callable(x) for x in (extract_product, fetcher_cls, extractor_cls)):
            raise ExtractionUnavailable(
                "styleid_charts does not expose extract_product, HttpxFetcher and ClaudeExtractor"
            )
        assert extract_product is not None and fetcher_cls is not None  # for the type checker
        assert extractor_cls is not None
        result: Any = extract_product(
            url,
            fetcher=fetcher_cls(),
            extractor=extractor_cls(model=model),
            garment_kind=garment_kind,
        )
        chart = getattr(result, "chart", result)
        if isinstance(chart, NormalisedChart):
            return chart
        return NormalisedChart.model_validate(chart)

    return extract


default_extract: ExtractFn = make_default_extract()


def _catalogue_garment(product: Product, size: Any, label: str) -> Garment:
    dumped = size.model_dump(mode="json")
    return Garment(
        product_id=product.id,
        size_label=label,
        kind=product.garment_kind,
        cut=dumped["cut"],
        stretch_class=dumped["stretch"],
        fit_tag=None,
        length_from_center_back=dumped["length_from_center_back"],
        sleeve_from_center_back=dumped["sleeve_from_center_back"],
        measurements=dumped["measurements"],
        is_reference=False,
    )


def apply_normalised_chart(
    db: Any, chart: SizeChart, product: Product, normalised: NormalisedChart
) -> None:
    """Store the result on the chart row; on OK replace the product's catalogue garments."""
    chart.normalised = normalised.model_dump(mode="json")
    chart.classification = normalised.classification.model_dump(mode="json")
    chart.model_id = normalised.model_id
    chart.status = SizeChartStatus(normalised.status.value).value
    chart.error = None
    chart.extracted_at = utcnow()
    if normalised.status is not ChartStatus.OK:
        return
    if not normalised.sizes:
        chart.status = SizeChartStatus.FAILED.value
        chart.error = "extraction reported ok but produced no sizes"
        return

    db.execute(delete(Garment).where(Garment.product_id == product.id))
    seen: set[str] = set()
    for index, size in enumerate(normalised.sizes):
        label = size.size_label or f"size-{index + 1}"
        if label in seen:
            log.warning("chart %s: duplicate size label %r skipped", chart.id, label)
            continue
        seen.add(label)
        db.add(_catalogue_garment(product, size, label))
    first = normalised.sizes[0]
    product.chart_id = chart.id
    product.stretch_class = (normalised.stretch or first.stretch).value
    product.fabric_composition = normalised.fabric_composition or product.fabric_composition
    product.cut = first.cut.value
    product.fetched_at = utcnow()


def process_size_chart(
    session_factory: SessionFactory, size_chart_id: str, extract_fn: ExtractFn
) -> None:
    """Run extraction for one pending chart row. Never raises: failures land in ``error``."""
    with session_factory() as db:
        chart = db.get(SizeChart, size_chart_id)
        if chart is None:
            log.warning("size chart %s vanished before extraction", size_chart_id)
            return
        product = db.get(Product, chart.product_id) if chart.product_id else None
        if product is None:
            chart.status = SizeChartStatus.FAILED.value
            chart.error = "size chart has no product"
            chart.extracted_at = utcnow()
            db.commit()
            return
        try:
            normalised = extract_fn(product.url_canonical, GarmentKind(product.garment_kind))
        except Exception as exc:  # recorded on the row and surfaced via the API
            log.exception("extraction failed for chart %s", size_chart_id)
            chart.status = SizeChartStatus.FAILED.value
            chart.error = f"{type(exc).__name__}: {exc}"
            chart.extracted_at = utcnow()
            db.commit()
            return
        apply_normalised_chart(db, chart, product, normalised)
        db.commit()


class InlineRunner:
    """Extract synchronously, in the request thread, with its own session."""

    def __init__(self, session_factory: SessionFactory, extract_fn: ExtractFn | None = None):
        self._session_factory = session_factory
        self._extract_fn: ExtractFn = extract_fn or default_extract

    def run(self, size_chart_id: str) -> None:
        process_size_chart(self._session_factory, size_chart_id, self._extract_fn)


def psycopg_conninfo(database_url: str) -> str:
    """``postgresql+psycopg://...`` -> ``postgresql://...`` for psycopg itself."""
    scheme, sep, rest = database_url.partition("://")
    return scheme.split("+", 1)[0] + sep + rest


def make_procrastinate_app(database_url: str, model: str | None = None) -> procrastinate.App:
    """A procrastinate app with the extraction task registered. The worker imports
    ``styleid_api.jobs.worker:app`` which calls this with the configured URL and model."""
    connector = procrastinate.PsycopgConnector(conninfo=psycopg_conninfo(database_url))
    app = procrastinate.App(connector=connector)
    extract_fn = make_default_extract(model)

    @app.task(name=TASK_NAME, queue=QUEUE_NAME)
    def extract_size_chart(size_chart_id: str) -> None:
        engine = make_engine(database_url)
        try:
            process_size_chart(make_session_factory(engine), size_chart_id, extract_fn)
        finally:
            engine.dispose()

    return app


class QueueRunner:
    """Defer a procrastinate job; the worker process does the extraction."""

    def __init__(self, app: procrastinate.App):
        self._app = app

    def run(self, size_chart_id: str) -> None:
        with self._app.open():
            self._app.configure_task(name=TASK_NAME, queue=QUEUE_NAME).defer(
                size_chart_id=size_chart_id
            )
