"""Pydantic v2 schemas for fee structures, invoices and payments.

All money fields are integer cents in ``currency`` minor units. Shape/type
checks live here (422 on bad payloads); cross-field business rules live in
``app.services.finance`` and surface as HTTP 400.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.models.finance import InvoiceStatus, PaymentMethod
from app.schemas.common import ORMModel


class FeeStructureCreate(BaseModel):
    school_id: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    category: str = Field(default="tuition", min_length=1, max_length=40)
    amount_cents: int = Field(ge=0, description="Fee price in minor units (cents).")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    is_active: bool = True

    @field_validator("currency")
    @classmethod
    def _normalise_currency(cls, value: str) -> str:
        return value.upper()


class FeeStructureRead(ORMModel):
    id: int
    school_id: int
    name: str
    description: str | None
    category: str
    amount_cents: int
    currency: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class InvoiceCreate(BaseModel):
    """Invoice input. ``amount_cents`` overrides the fee structure price
    (scholarships/adjustments); without a fee structure it is required and a
    ``description`` must be given.
    """

    student_id: int = Field(ge=1)
    fee_structure_id: int | None = Field(default=None, ge=1)
    amount_cents: int | None = Field(default=None, ge=1)
    description: str | None = Field(default=None, max_length=255)
    issue_date: date | None = None
    due_date: date | None = None


class PaymentCreate(BaseModel):
    amount_cents: int = Field(gt=0)
    method: PaymentMethod = PaymentMethod.CASH
    reference: str | None = Field(default=None, max_length=64)
    note: str | None = Field(default=None, max_length=255)
    #: Defaults to today when omitted.
    paid_on: date | None = None


class PaymentRead(ORMModel):
    id: int
    invoice_id: int
    receipt_number: str | None
    amount_cents: int
    method: PaymentMethod
    reference: str | None
    note: str | None
    paid_on: date
    recorded_at: datetime


class InvoiceRead(ORMModel):
    """Full invoice view; balance fields are filled by the service layer."""

    id: int
    number: str | None
    school_id: int
    student_id: int
    student_name: str | None = None
    fee_structure_id: int | None
    fee_structure_name: str | None = None
    description: str | None
    amount_cents: int
    currency: str
    issue_date: date
    due_date: date
    status: InvoiceStatus
    payments: list[PaymentRead] = Field(default_factory=list)
    paid_cents: int = 0
    balance_cents: int = 0
    is_overdue: bool = False
    created_at: datetime
    updated_at: datetime


class InvoiceBalance(BaseModel):
    """Compact balance snapshot for a single invoice."""

    invoice_id: int
    number: str | None
    status: InvoiceStatus
    currency: str
    amount_cents: int
    paid_cents: int
    balance_cents: int
    due_date: date
    is_overdue: bool


class StudentBalance(BaseModel):
    """Aggregated ledger view for one student (void invoices excluded)."""

    student_id: int
    full_name: str
    currency: str
    invoiced_cents: int
    paid_cents: int
    balance_cents: int
    invoice_count: int
    open_invoice_count: int
    overdue_invoice_count: int
