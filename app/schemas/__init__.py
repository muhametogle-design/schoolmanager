"""Pydantic v2 schemas.

Explicit static re-exports only (project architecture rule: no dynamic
loading loops).
"""

from app.schemas.common import EmailMixin, ORMModel
from app.schemas.finance import (
    FeeStructureCreate,
    FeeStructureRead,
    InvoiceBalance,
    InvoiceCreate,
    InvoiceRead,
    PaymentCreate,
    PaymentRead,
    StudentBalance,
)
from app.schemas.management import (
    SchoolCreate,
    SchoolRead,
    StudentCreate,
    StudentRead,
    StudentUpdate,
)

__all__ = [
    "EmailMixin",
    "FeeStructureCreate",
    "FeeStructureRead",
    "InvoiceBalance",
    "InvoiceCreate",
    "InvoiceRead",
    "ORMModel",
    "PaymentCreate",
    "PaymentRead",
    "SchoolCreate",
    "SchoolRead",
    "StudentBalance",
    "StudentCreate",
    "StudentRead",
    "StudentUpdate",
]
