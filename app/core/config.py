"""Application configuration for the NE-ES School Management System.

Settings live in a single frozen dataclass so the rest of the codebase receives
an explicit, typed configuration object. Environment variables prefixed with
``SCHOOLMGR_`` override the defaults and are read once, in ``get_settings()``.
Tests build their own :class:`Settings` instances pointing at temp
directories, which keeps the production defaults untouched.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_DIR.parent

DEFAULT_APP_NAME = "NE-ES School Management System"
DEFAULT_DATABASE_URL = f"sqlite:///{REPO_ROOT / 'data' / 'schoolmanager.db'}"
DEFAULT_STATIC_ROOT = APP_DIR / "static"
DEFAULT_MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MiB per uploaded image

#: Sub-directories under ``<static_root>/uploads`` that the storage service may
#: write to. Kept as an explicit, static tuple (no discovery loops).
UPLOAD_SUBDIRS: tuple[str, ...] = ("avatars", "logos")


def _env(name: str) -> str | None:
    raw = os.environ.get(name)
    if raw is None:
        return None
    raw = raw.strip()
    return raw or None


@dataclass(frozen=True, slots=True)
class Settings:
    """Typed application settings (see module docstring for env overrides)."""

    app_name: str = DEFAULT_APP_NAME
    database_url: str = DEFAULT_DATABASE_URL
    static_root: Path = DEFAULT_STATIC_ROOT
    max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES
    upload_subdirs: tuple[str, ...] = UPLOAD_SUBDIRS

    @property
    def uploads_root(self) -> Path:
        """Root directory for stored uploads (served under ``/static``)."""
        return self.static_root / "uploads"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Build settings from the environment once (cached)."""
    overrides: dict[str, object] = {}
    if raw := _env("SCHOOLMGR_APP_NAME"):
        overrides["app_name"] = raw
    if raw := _env("SCHOOLMGR_DATABASE_URL"):
        overrides["database_url"] = raw
    if raw := _env("SCHOOLMGR_STATIC_ROOT"):
        overrides["static_root"] = Path(raw).expanduser()
    if raw := _env("SCHOOLMGR_MAX_UPLOAD_BYTES"):
        overrides["max_upload_bytes"] = int(raw)
    return Settings(**overrides)
