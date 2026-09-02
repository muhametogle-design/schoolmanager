"""SQLAlchemy ORM models.

Explicit static imports only (project architecture rule: no dynamic loading
loops). Importing this package loads every mapped class so that
``Base.metadata`` is complete for ``create_all()`` and relationship resolution.
"""

from app.models.base import Base, TimestampMixin, utcnow
from app.models.finance import (
    FeeStructure,
    Invoice,
    InvoiceStatus,
    Payment,
    PaymentMethod,
)
from app.models.management import School, Student

__all__ = [
    "Base",
    "FeeStructure",
    "Invoice",
    "InvoiceStatus",
    "Payment",
    "PaymentMethod",
    "School",
    "Student",
    "TimestampMixin",
    "utcnow",
]
