"""Application factory."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from sqlalchemy import Engine
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from . import __version__
from .auth.apple import AppleVerifier, CachedJWKS, JWKSProvider
from .auth.router import router as auth_router
from .config import Settings
from .db.session import SessionFactory, create_all, make_engine, make_session_factory
from .jobs.extraction import (
    ExtractFn,
    ExtractionRunner,
    InlineRunner,
    QueueRunner,
    make_default_extract,
    make_procrastinate_app,
)
from .openapi import operation_id_for
from .routers import body, closet, fit, health, me, outcomes, products


class RequestIdMiddleware:
    """Echo or mint ``X-Request-ID`` and expose it as ``request.state.request_id``."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = Headers(scope=scope).get("x-request-id") or uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message).append("X-Request-ID", request_id)
            await send(message)

        await self.app(scope, receive, send_with_id)


def build_runner(
    settings: Settings, session_factory: SessionFactory, extract_fn: ExtractFn | None = None
) -> ExtractionRunner:
    if settings.extraction_runner == "queue":
        return QueueRunner(
            make_procrastinate_app(settings.database_url, settings.chart_extraction_model)
        )
    return InlineRunner(
        session_factory, extract_fn or make_default_extract(settings.chart_extraction_model)
    )


def create_app(
    settings: Settings | None = None,
    runner: ExtractionRunner | None = None,
    *,
    extract_fn: ExtractFn | None = None,
    jwks_provider: JWKSProvider | None = None,
    engine: Engine | None = None,
) -> FastAPI:
    """Build the app. Tests pass a SQLite ``Settings``, a fake ``extract_fn`` and a
    ``jwks_provider`` returning a locally generated key set."""
    settings = settings or Settings()
    engine = engine or make_engine(settings.database_url)
    session_factory = make_session_factory(engine)
    runner = runner or build_runner(settings, session_factory, extract_fn)
    jwks = jwks_provider or CachedJWKS(
        settings.apple_jwks_url, ttl_seconds=settings.apple_jwks_ttl_seconds
    )
    verifier = AppleVerifier(
        client_id=settings.apple_client_id, issuer=settings.apple_issuer, jwks=jwks
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if settings.auto_create_tables:
            create_all(engine)
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(
        title="style.id API",
        version=__version__,
        description="Measurement-based fit for tops: closet, body, products, fit reports.",
        lifespan=lifespan,
        generate_unique_id_function=operation_id_for,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.extraction_runner = runner
    app.state.apple_verifier = verifier
    app.add_middleware(RequestIdMiddleware)

    v1 = APIRouter(prefix="/v1")
    for router in (
        health.router,
        auth_router,
        me.router,
        closet.router,
        body.router,
        products.router,
        fit.router,
        outcomes.router,
    ):
        v1.include_router(router)
    app.include_router(v1)
    return app


app = create_app()
