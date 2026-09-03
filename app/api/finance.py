"""Finance & fees API: fee structures, invoices, payments and balances.

All amounts are integer cents (minor units of ``currency``). Route handlers
stay thin: they parse payloads, delegate to ``FinanceService`` and return
schemas. Business-rule violations bubble up as ``ServiceError``s and are
mapped to JSON responses by the handler in ``app.main``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import FinanceServiceDep
from app.models.finance import InvoiceStatus, PaymentMethod
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

router = APIRouter(prefix="/finance", tags=["finance"])


# -- fee structures ------------------------------------------------------------


@router.get("/fee-structures", response_model=list[FeeStructureRead])
def list_fee_structures(
    service: FinanceServiceDep,
    school_id: Annotated[int | None, Query(ge=1)] = None,
) -> list[FeeStructureRead]:
    fees = service.list_fee_structures(school_id)
    return [FeeStructureRead.model_validate(fee) for fee in fees]


@router.post("/fee-structures", response_model=FeeStructureRead, status_code=201)
def create_fee_structure(
    payload: FeeStructureCreate, service: FinanceServiceDep
) -> FeeStructureRead:
    fee = service.create_fee_structure(payload)
    return FeeStructureRead.model_validate(fee)


@router.get("/fee-structures/{fee_structure_id}", response_model=FeeStructureRead)
def get_fee_structure(fee_structure_id: int, service: FinanceServiceDep) -> FeeStructureRead:
    return FeeStructureRead.model_validate(service.get_fee_structure(fee_structure_id))


# -- invoices ----------------------------------------------------------------------


@router.get("/invoices", response_model=list[InvoiceRead])
def list_invoices(
    service: FinanceServiceDep,
    student_id: Annotated[int | None, Query(ge=1)] = None,
    status: Annotated[InvoiceStatus | None, Query()] = None,
) -> list[InvoiceRead]:
    return service.read_invoices(service.list_invoices(student_id=student_id, status=status))


@router.post("/invoices", response_model=InvoiceRead, status_code=201)
def create_invoice(payload: InvoiceCreate, service: FinanceServiceDep) -> InvoiceRead:
    return service.read_invoice(service.create_invoice(payload))


@router.get("/invoices/{invoice_id}", response_model=InvoiceRead)
def get_invoice(invoice_id: int, service: FinanceServiceDep) -> InvoiceRead:
    return service.read_invoice(service.get_invoice(invoice_id))


@router.post("/invoices/{invoice_id}/void", response_model=InvoiceRead)
def void_invoice(invoice_id: int, service: FinanceServiceDep) -> InvoiceRead:
    return service.read_invoice(service.void_invoice(invoice_id))


@router.get("/invoices/{invoice_id}/balance", response_model=InvoiceBalance)
def get_invoice_balance(invoice_id: int, service: FinanceServiceDep) -> InvoiceBalance:
    return service.invoice_balance(invoice_id)


# -- payments --------------------------------------------------------------------------


@router.post("/invoices/{invoice_id}/payments", response_model=PaymentRead, status_code=201)
def record_payment(
    invoice_id: int, payload: PaymentCreate, service: FinanceServiceDep
) -> PaymentRead:
    return PaymentRead.model_validate(service.record_payment(invoice_id, payload))


@router.get("/invoices/{invoice_id}/payments", response_model=list[PaymentRead])
def list_invoice_payments(invoice_id: int, service: FinanceServiceDep) -> list[PaymentRead]:
    payments = service.list_payments(invoice_id=invoice_id)
    return [PaymentRead.model_validate(payment) for payment in payments]


@router.get("/payments", response_model=list[PaymentRead])
def list_payments(
    service: FinanceServiceDep,
    invoice_id: Annotated[int | None, Query(ge=1)] = None,
    student_id: Annotated[int | None, Query(ge=1)] = None,
    method: Annotated[PaymentMethod | None, Query()] = None,
) -> list[PaymentRead]:
    payments = service.list_payments(invoice_id=invoice_id, student_id=student_id)
    if method is not None:
        payments = [p for p in payments if p.method is method]
    return [PaymentRead.model_validate(payment) for payment in payments]


# -- balances ----------------------------------------------------------------------------


@router.get("/students/{student_id}/balance", response_model=StudentBalance)
def get_student_balance(student_id: int, service: FinanceServiceDep) -> StudentBalance:
    return service.student_balance(student_id)
