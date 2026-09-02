"""NE-ES School Management System - FastAPI application entry point.

Run in development::

    uvicorn app.main:app --reload

Deployment::

    uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import academics, auth, management, students
from app.core.config import settings
from app.db.session import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Create tables and seed the default school/admin on startup."""
    init_db(seed=True)
    yield


app = FastAPI(
    title=settings.app_name,
    description=(
        "REST API for the NE-ES School Management System: authentication, "
        "student records, academic management (classes & subjects) and "
        "school UI configuration."
    ),
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# --- Router registration ----------------------------------------------------
# Every router is registered with an explicit prefix and tag group so the
# OpenAPI docs stay organised and imports stay static.
app.include_router(auth.router)                 # /auth/*
app.include_router(students.router)             # /students/*
app.include_router(academics.router)            # /academics/*
app.include_router(management.router)           # /management/*


@app.get("/", tags=["Health"], summary="Health check")
def health_check() -> dict[str, str]:
    """Root health check endpoint."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }
