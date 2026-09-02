"""NE-ES School Management System — FastAPI entry point.

Wiring is deliberately explicit (project architecture rule: no dynamic router
discovery): the routers exported by ``app.api`` are included here, uploads are
served from a static mount backed by ``app/static/``, and service-layer
errors are translated into JSON responses by one exception handler.

Run locally with::

    uvicorn app.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api import finance_router, management_router
from app.core.config import Settings, get_settings
from app.core.db import create_db_engine, make_session_factory
from app.core.errors import ServiceError
from app.models import Base
from app.services.storage import FileStorageService

API_V1_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory.

    Tests call ``create_app(Settings(...))`` with temp-dir overrides so every
    run gets an isolated database plus uploads directory without touching the
    repo defaults.
    """
    settings = settings or get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Backend for the NE-ES School Management System: student records "
            "with photo uploads, plus finance & fees (fee structures, "
            "invoices, payments, balances)."
        ),
    )

    engine = create_db_engine(settings.database_url)
    storage = FileStorageService(
        settings.uploads_root,
        max_bytes=settings.max_upload_bytes,
        allowed_subdirs=settings.upload_subdirs,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.state.storage = storage

    # Uploads live inside the static tree so they are servable; create the
    # directories before the StaticFiles mount validates them, then ensure the
    # schema exists (no migration tool in this milestone).
    storage.ensure_dirs()
    Base.metadata.create_all(bind=engine)

    @app.exception_handler(ServiceError)
    async def handle_service_error(_request: Request, exc: ServiceError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    app.include_router(management_router, prefix=API_V1_PREFIX)
    app.include_router(finance_router, prefix=API_V1_PREFIX)

    app.mount(
        "/static",
        StaticFiles(directory=str(settings.static_root)),
        name="static",
    )

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name, "version": __version__}

    return app


app = create_app()
