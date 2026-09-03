"""FastAPI dependency wiring for routes.

Everything is wired explicitly with typed ``Annotated`` aliases — no dynamic
plugin loading or import loops. Services are constructed per request from
state that ``app.main.create_app`` installed.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.services.finance import FinanceService
from app.services.management import ManagementService
from app.services.storage import FileStorageService


def get_db(request: Request) -> Iterator[Session]:
    """Yield a request-scoped session; roll back on unhandled errors."""
    session: Session = request.app.state.session_factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_storage(request: Request) -> FileStorageService:
    storage: FileStorageService = request.app.state.storage
    return storage


def get_management_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[FileStorageService, Depends(get_storage)],
) -> ManagementService:
    return ManagementService(db, storage)


def get_finance_service(
    db: Annotated[Session, Depends(get_db)],
) -> FinanceService:
    return FinanceService(db)


DbSession = Annotated[Session, Depends(get_db)]
StorageDep = Annotated[FileStorageService, Depends(get_storage)]
ManagementServiceDep = Annotated[ManagementService, Depends(get_management_service)]
FinanceServiceDep = Annotated[FinanceService, Depends(get_finance_service)]
