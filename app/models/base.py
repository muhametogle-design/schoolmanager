"""Common model plumbing: the declarative ``Base`` and shared column mixins."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Timezone-aware UTC timestamp used by Python-side column defaults."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Single declarative base shared by every model module."""


class TimestampMixin:
    """``created_at`` / ``updated_at`` bookkeeping for audited tables."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
