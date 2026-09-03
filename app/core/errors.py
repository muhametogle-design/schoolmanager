"""Service-layer error types.

Services raise these typed errors instead of FastAPI ``HTTPException``s, which
keeps business logic testable without a web layer. ``app.main`` registers one
exception handler that translates them into JSON responses using each class's
``status_code``.
"""

from __future__ import annotations


class ServiceError(Exception):
    """Request-level failure raised by services (maps to HTTP 400)."""

    status_code: int = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(ServiceError):
    """A referenced record does not exist (maps to HTTP 404)."""

    status_code: int = 404


class PayloadTooLargeError(ServiceError):
    """An uploaded file exceeds the configured limit (maps to HTTP 413)."""

    status_code: int = 413


class StorageError(ServiceError):
    """The file system refused to persist/remove a file (maps to HTTP 500)."""

    status_code: int = 500
