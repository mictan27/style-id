"""Engine and session factory. Sync SQLAlchemy 2.0; fine for the beta."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from fastapi import Request
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

SessionFactory = sessionmaker[Session]


def make_engine(database_url: str, **kwargs: Any) -> Engine:
    """Create an engine. SQLite gets ``check_same_thread=False`` (FastAPI's threadpool)
    and ``PRAGMA foreign_keys=ON`` on every connection so FKs behave like Postgres."""
    if database_url.startswith("sqlite"):
        connect_args = dict(kwargs.pop("connect_args", {}))
        connect_args.setdefault("check_same_thread", False)
        engine = create_engine(database_url, connect_args=connect_args, **kwargs)

        @event.listens_for(engine, "connect")
        def _enable_fks(dbapi_connection: Any, _record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine
    return create_engine(database_url, pool_pre_ping=True, **kwargs)


def make_session_factory(engine: Engine) -> SessionFactory:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_all(engine: Engine) -> None:
    """Create every table from the models. Tests and the SQLite dev loop use this; real
    deployments run ``alembic upgrade head``."""
    Base.metadata.create_all(engine)


def get_db(request: Request) -> Iterator[Session]:
    """FastAPI dependency: one session per request, bound to the app's factory."""
    factory: SessionFactory = request.app.state.session_factory
    with factory() as session:
        yield session
