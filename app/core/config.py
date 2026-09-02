"""Application configuration loaded from environment variables / a .env file."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repository root: <root>/app/core/config.py -> three levels up.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Runtime settings. Every value can be overridden with an environment
    variable of the same name (case-insensitive), e.g. ``DATABASE_URL``,
    ``SECRET_KEY``, ``DEFAULT_ADMIN_PASSWORD``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "NE-ES School Management System"
    app_version: str = "1.0.0"
    debug: bool = False

    # --- Database ---
    # SQLite by default for a zero-config deployment. Point DATABASE_URL at a
    # Postgres/MySQL server for production use.
    database_url: str = f"sqlite:///{BASE_DIR / 'schoolmanager.db'}"

    # --- Security ---
    secret_key: str = "dev-only-secret-change-me-in-production"
    token_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # --- Default seed data (used on first startup) ---
    default_school_name: str = "NE-ES Academy"
    default_admin_username: str = "admin"
    default_admin_password: str = "admin123"


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings instance."""
    return Settings()


settings = get_settings()
