"""SQLAlchemy declarative base shared by every ORM model."""
from datetime import UTC, datetime

from sqlalchemy.orm import DeclarativeBase


def utcnow() -> datetime:
    """Current UTC time; usable as a column default/onupdate callable."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Standard declarative base for the whole application.

    Concrete models (app.models.*) subclass this class so that their tables
    are collected on ``Base.metadata`` and created by ``init_db()``.
    """
