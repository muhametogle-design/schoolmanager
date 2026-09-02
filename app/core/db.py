"""SQLAlchemy engine and session factories.

This module deliberately knows nothing about the ORM models (``app.models``
owns the declarative ``Base``); wiring happens explicitly in
``app.main.create_app``.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

_SQLITE_MEMORY_URLS = frozenset({"sqlite://", "sqlite:///:memory:"})


def create_db_engine(database_url: str) -> Engine:
    """Create an engine, preparing local SQLite files/dirs as needed."""
    connect_args: dict[str, object] = {}
    extra: dict[str, object] = {}
    if database_url.startswith("sqlite"):
        # Sessions are handed to FastAPI worker threads; SQLite's own
        # thread-affinity check has to be relaxed.
        connect_args["check_same_thread"] = False
        if database_url in _SQLITE_MEMORY_URLS:
            extra["poolclass"] = StaticPool
        else:
            db_path = Path(database_url.removeprefix("sqlite:///")).expanduser()
            if str(db_path):
                db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(database_url, echo=False, connect_args=connect_args, **extra)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Build a request-scoped session factory.

    ``expire_on_commit=False`` keeps loaded attributes (and eagerly loaded
    relationships) readable while a response schema is being constructed,
    even after the service layer commits.
    """
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
