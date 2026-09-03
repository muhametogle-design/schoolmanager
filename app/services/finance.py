"""Finance business logic: fee structures, invoicing, payments and balances.

Rules enforced here (surfaced as HTTP 400/404 via ``ServiceError``):

* an invoice draws its amount from a fee structure or an explicit override —
  one of the two is mandatory;
* a fee structure can only be invoiced against a student of the same school;
* ``due_date`` may not precede ``issue_date``;
* payments are rejected once the invoice is fully paid or void, and must not
  exceed the outstanding balance (no credit balances);
* the invoice status is recomputed on every payment; overdue-ness is derived
  from status + due date + balance at read time.

Monetary arithmetic is integer-cent only. Balances assume a single currency
per student, which mirrors the school's fee plan.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta
from typing import Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ServiceError
from app.models.finance import FeeStructure, Invoice, InvoiceStatus, Payment
from app.models.management import School, Student
from app.schemas.finance import (
    FeeStructureCreate,
    InvoiceBalance,
    InvoiceCreate,
    InvoiceRead,
    PaymentCreate,
    StudentBalance,
)

DEFAULT_CURRENCY: Final = "USD"
#: Default payment term when the caller does not pin a due date.
DEFAULT_PAYMENT_TERM_DAYS: Final = 30


class FinanceService:
    def __init__(self, session: Session) -> None:
        self._session = session

    # -- fee structures ------------------------------------------------------

    def create_fee_structure(self, payload: FeeStructureCreate) -> FeeStructure:
        self._get_school(payload.school_id)
        duplicate = self._session.scalar(
            select(FeeStructure.id).where(
                FeeStructure.school_id == payload.school_id,
                FeeStructure.name == payload.name,
            )
        )
        if duplicate is not None:
            raise ServiceError(f"fee structure {payload.name!r} already exists for this school")
        fee_structure = FeeStructure(**payload.model_dump())
        self._session.add(fee_structure)
        self._session.commit()
        return fee_structure

    def list_fee_structures(self, school_id: int | None = None) -> Sequence[FeeStructure]:
        stmt = select(FeeStructure).order_by(FeeStructure.id)
        if school_id is not None:
            self._get_school(school_id)  # 404 signal for an unknown filter
            stmt = stmt.where(FeeStructure.school_id == school_id)
        return self._session.scalars(stmt).all()

    def get_fee_structure(self, fee_structure_id: int) -> FeeStructure:
        fee_structure = self._session.get(FeeStructure, fee_structure_id)
        if fee_structure is None:
            raise NotFoundError(f"fee structure {fee_structure_id} not found")
        return fee_structure

    # -- invoices --------------------------------------------------------------

    def create_invoice(self, payload: InvoiceCreate) -> Invoice:
        student = self._session.get(Student, payload.student_id)
        if student is None:
            raise NotFoundError(f"student {payload.student_id} not found")

        fee_structure: FeeStructure | None = None
        if payload.fee_structure_id is not None:
            fee_structure = self.get_fee_structure(payload.fee_structure_id)
            if not fee_structure.is_active:
                raise ServiceError(
                    f"fee structure {fee_structure.name!r} is inactive and cannot be invoiced"
                )
            if fee_structure.school_id != student.school_id:
                raise ServiceError(
                    "fee structure belongs to a different school than the student"
                )

        if payload.amount_cents is not None:
            amount_cents = payload.amount_cents
        elif fee_structure is not None:
            amount_cents = fee_structure.amount_cents
            if amount_cents <= 0:
                raise ServiceError(
                    f"fee structure {fee_structure.name!r} has a zero amount; "
                    "pass an explicit amount_cents to invoice it"
                )
        else:
            raise ServiceError("amount_cents is required when no fee_structure_id is provided")

        description = payload.description or (fee_structure.name if fee_structure else None)
        if not description:
            raise ServiceError("description is required when invoicing a custom amount")

        issue_date = payload.issue_date or date.today()
        due_date = payload.due_date or (issue_date + timedelta(days=DEFAULT_PAYMENT_TERM_DAYS))
        if due_date < issue_date:
            raise ServiceError("due_date cannot be earlier than issue_date")

        invoice = Invoice(
            school_id=student.school_id,
            student_id=student.id,
            fee_structure_id=fee_structure.id if fee_structure else None,
            description=description,
            amount_cents=amount_cents,
            currency=fee_structure.currency if fee_structure else DEFAULT_CURRENCY,
            issue_date=issue_date,
            due_date=due_date,
            status=InvoiceStatus.ISSUED,
        )
        self._session.add(invoice)
        self._session.flush()
        invoice.number = f"INV-{issue_date.year}-{invoice.id:05d}"
        self._session.commit()
        return invoice

    def get_invoice(self, invoice_id: int) -> Invoice:
        # FOR UPDATE serialises concurrent payments on PostgreSQL; SQLite
        # compiles this away, so it is safe to keep unconditionally.
        invoice = self._session.scalar(
            select(Invoice).where(Invoice.id == invoice_id).with_for_update()
        )
        if invoice is None:
            raise NotFoundError(f"invoice {invoice_id} not found")
        return invoice

    def list_invoices(
        self,
        student_id: int | None = None,
        status: InvoiceStatus | None = None,
    ) -> Sequence[Invoice]:
        stmt = select(Invoice).order_by(Invoice.id)
        if student_id is not None:
            if self._session.get(Student, student_id) is None:
                raise NotFoundError(f"student {student_id} not found")
            stmt = stmt.where(Invoice.student_id == student_id)
        if status is not None:
            stmt = stmt.where(Invoice.status == status)
        return self._session.scalars(stmt).all()

    def void_invoice(self, invoice_id: int) -> Invoice:
        invoice = self.get_invoice(invoice_id)
        if invoice.status is InvoiceStatus.VOID:
            raise ServiceError("invoice is already void")
        if self._paid_cents(invoice) > 0:
            raise ServiceError("cannot void an invoice that already has recorded payments")
        invoice.status = InvoiceStatus.VOID
        self._session.commit()
        return invoice

    # -- payments ---------------------------------------------------------------

    def record_payment(self, invoice_id: int, payload: PaymentCreate) -> Payment:
        invoice = self.get_invoice(invoice_id)
        if invoice.status is InvoiceStatus.VOID:
            raise ServiceError("cannot record payments against a void invoice")

        outstanding = invoice.amount_cents - self._paid_cents(invoice)
        if outstanding <= 0:
            raise ServiceError(f"invoice {invoice.number or invoice.id} is already fully paid")
        if payload.amount_cents > outstanding:
            raise ServiceError(
                f"payment of {payload.amount_cents} cents exceeds the outstanding "
                f"balance of {outstanding} cents"
            )

        payment = Payment(
            invoice=invoice,
            amount_cents=payload.amount_cents,
            method=payload.method,
            reference=payload.reference,
            note=payload.note,
            paid_on=payload.paid_on or date.today(),
        )
        self._session.add(payment)
        self._session.flush()
        payment.receipt_number = f"RCP-{payment.paid_on.year}-{payment.id:05d}"

        total_paid = self._paid_cents(invoice)
        if total_paid >= invoice.amount_cents:
            invoice.status = InvoiceStatus.PAID
        else:
            invoice.status = InvoiceStatus.PARTIALLY_PAID
        self._session.commit()
        return payment

    def list_payments(
        self,
        *,
        invoice_id: int | None = None,
        student_id: int | None = None,
    ) -> Sequence[Payment]:
        stmt = (
            select(Payment)
            .join(Invoice, Payment.invoice_id == Invoice.id)
            .order_by(Payment.id)
        )
        if invoice_id is not None:
            self.get_invoice(invoice_id)  # 404 signal for an unknown filter
            stmt = stmt.where(Payment.invoice_id == invoice_id)
        if student_id is not None:
            if self._session.get(Student, student_id) is None:
                raise NotFoundError(f"student {student_id} not found")
            stmt = stmt.where(Invoice.student_id == student_id)
        return self._session.scalars(stmt).all()

    # -- balances ---------------------------------------------------------------

    def invoice_balance(self, invoice_id: int) -> InvoiceBalance:
        invoice = self.get_invoice(invoice_id)
        paid_cents = self._paid_cents(invoice)
        balance_cents = max(invoice.amount_cents - paid_cents, 0)
        return InvoiceBalance(
            invoice_id=invoice.id,
            number=invoice.number,
            status=invoice.status,
            currency=invoice.currency,
            amount_cents=invoice.amount_cents,
            paid_cents=paid_cents,
            balance_cents=balance_cents,
            due_date=invoice.due_date,
            is_overdue=self._is_overdue(invoice, balance_cents),
        )

    def student_balance(self, student_id: int) -> StudentBalance:
        student = self._session.get(Student, student_id)
        if student is None:
            raise NotFoundError(f"student {student_id} not found")
        invoices = [
            invoice
            for invoice in self._session.scalars(
                select(Invoice).where(Invoice.student_id == student_id).order_by(Invoice.id)
            ).all()
            if invoice.status is not InvoiceStatus.VOID
        ]
        invoiced_cents = 0
        paid_cents = 0
        open_count = 0
        overdue_count = 0
        for invoice in invoices:
            invoice_paid = self._paid_cents(invoice)
            invoice_balance = max(invoice.amount_cents - invoice_paid, 0)
            invoiced_cents += invoice.amount_cents
            paid_cents += invoice_paid
            if invoice_balance > 0:
                open_count += 1
                if self._is_overdue(invoice, invoice_balance):
                    overdue_count += 1
        currency = invoices[0].currency if invoices else DEFAULT_CURRENCY
        return StudentBalance(
            student_id=student.id,
            full_name=student.full_name,
            currency=currency,
            invoiced_cents=invoiced_cents,
            paid_cents=paid_cents,
            balance_cents=max(invoiced_cents - paid_cents, 0),
            invoice_count=len(invoices),
            open_invoice_count=open_count,
            overdue_invoice_count=overdue_count,
        )

    # -- read-model builders -----------------------------------------------------

    def read_invoice(self, invoice: Invoice) -> InvoiceRead:
        """Compose the read schema with derived balance fields."""
        paid_cents = self._paid_cents(invoice)
        balance_cents = max(invoice.amount_cents - paid_cents, 0)
        return InvoiceRead.model_validate(invoice).model_copy(
            update={
                "paid_cents": paid_cents,
                "balance_cents": balance_cents,
                "is_overdue": self._is_overdue(invoice, balance_cents),
                "student_name": invoice.student.full_name,
                "fee_structure_name": invoice.fee_structure.name if invoice.fee_structure else None,
            }
        )

    def read_invoices(self, invoices: Sequence[Invoice]) -> list[InvoiceRead]:
        return [self.read_invoice(invoice) for invoice in invoices]

    # -- helpers ------------------------------------------------------------------

    def _paid_cents(self, invoice: Invoice) -> int:
        # ``payments`` is eagerly loaded (lazy="selectin"), so this stays in
        # memory; freshly flushed payments are already in the collection.
        return sum(payment.amount_cents for payment in invoice.payments)

    def _is_overdue(self, invoice: Invoice, balance_cents: int) -> bool:
        if balance_cents <= 0 or invoice.status in (InvoiceStatus.PAID, InvoiceStatus.VOID):
            return False
        return invoice.due_date < date.today()

    def _get_school(self, school_id: int) -> School:
        school = self._session.get(School, school_id)
        if school is None:
            raise NotFoundError(f"school {school_id} not found")
        return school
