"""Finance & fees domain models: :class:`FeeStructure`, :class:`Invoice`,
:class:`Payment`.

Design notes:

* Money is stored as **integer cents** (minor units) to avoid float/Decimal
  rounding issues on SQLite; ``currency`` records the ISO-4217 code the
  amounts belong to.
* One fee component per invoice keeps the ledger auditable: each invoice owns
  its issue/due dates, status, payments and balance.
* Invoice and receipt numbers are derived from the primary key right after
  flush, which guarantees uniqueness without extra locking.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, utcnow

if TYPE_CHECKING:
    from app.models.management import School, Student


class InvoiceStatus(StrEnum):
    """Lifecycle of an invoice. Overdue-ness is derived at read time."""

    ISSUED = "issued"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    VOID = "void"


class PaymentMethod(StrEnum):
    CASH = "cash"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    CHECK = "check"
    MOBILE = "mobile"


def _enum_column(enum_cls: type[StrEnum]) -> Enum:
    """VARCHAR-backed enum column storing lowercase values (portable)."""
    return Enum(
        enum_cls,
        native_enum=False,
        validate_strings=True,
        length=24,
        values_callable=lambda cls: [member.value for member in cls],
    )


class FeeStructure(TimestampMixin, Base):
    """A named, priced fee component of a school's fee plan."""

    __tablename__ = "fee_structures"
    __table_args__: ClassVar = (
        UniqueConstraint("school_id", "name", name="uq_fee_structure_school_name"),
        CheckConstraint("amount_cents >= 0", name="ck_fee_structure_amount_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    #: Free-form grouping key: tuition, transport, exams, activities, ...
    category: Mapped[str] = mapped_column(String(40), nullable=False, default="tuition")
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    school: Mapped[School] = relationship()
    invoices: Mapped[list[Invoice]] = relationship(back_populates="fee_structure")


class Invoice(TimestampMixin, Base):
    """A single payable bill issued to one student."""

    __tablename__ = "invoices"
    __table_args__: ClassVar = (
        UniqueConstraint("number", name="uq_invoices_number"),
        CheckConstraint("amount_cents > 0", name="ck_invoice_amount_positive"),
        CheckConstraint("due_date >= issue_date", name="ck_invoice_due_on_or_after_issue"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    #: Human-readable ledger reference, e.g. ``INV-2026-00042`` (set on flush).
    number: Mapped[str | None] = mapped_column(String(32))
    #: Denormalised tenancy column so reports can filter by school directly.
    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"), index=True, nullable=False
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    #: ``SET NULL`` so historical invoices survive fee-plan edits/removals.
    fee_structure_id: Mapped[int | None] = mapped_column(
        ForeignKey("fee_structures.id", ondelete="SET NULL"), index=True
    )
    description: Mapped[str | None] = mapped_column(String(255))
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        _enum_column(InvoiceStatus), nullable=False, default=InvoiceStatus.ISSUED
    )

    student: Mapped[Student] = relationship(back_populates="invoices", lazy="selectin")
    fee_structure: Mapped[FeeStructure | None] = relationship(
        back_populates="invoices", lazy="selectin"
    )
    payments: Mapped[list[Payment]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Payment.id",
    )


class Payment(TimestampMixin, Base):
    """An immutable money-in record applied to one invoice."""

    __tablename__ = "payments"
    __table_args__: ClassVar = (
        UniqueConstraint("receipt_number", name="uq_payments_receipt_number"),
        CheckConstraint("amount_cents > 0", name="ck_payment_amount_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), index=True, nullable=False
    )
    #: E.g. ``RCP-2026-00107`` (set on flush, after the primary key is known).
    receipt_number: Mapped[str | None] = mapped_column(String(32))
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        _enum_column(PaymentMethod), nullable=False, default=PaymentMethod.CASH
    )
    #: External transaction id (card auth code, bank transfer ref, ...).
    reference: Mapped[str | None] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(String(255))
    paid_on: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    invoice: Mapped[Invoice] = relationship(back_populates="payments")
