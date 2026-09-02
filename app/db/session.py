"""Engine, session factory, FastAPI dependency and database initialisation."""
from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base

_engine_kwargs: dict[str, Any] = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    # Allow the same in-memory/file SQLite connection to be shared across the
    # worker threads used by FastAPI's sync route handlers.
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.database_url, **_engine_kwargs)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(seed: bool = True) -> None:
    """Create all tables and (optionally) seed the default data.

    Importing ``app.models`` here - and only at call time - guarantees that
    every model module has been loaded and registered on ``Base.metadata``
    before tables are created, without introducing import cycles at startup.
    """
    import app.models as _models  # noqa: F401  - side-effect import: registers
    # every model on Base.metadata. The ``_ = ...`` reference keeps linters
    # from flagging the intentionally unused import.
    _ = _models

    Base.metadata.create_all(bind=engine)
    if seed:
        with SessionLocal() as db:
            seed_default_data(db)


def seed_default_data(db: Session) -> None:
    """Idempotently create the default school, admin user and UI config."""
    from app.models.identity import PrivateSchool, User
    from app.models.management import UiConfig

    school = db.scalar(
        select(PrivateSchool).order_by(PrivateSchool.id).limit(1)
    )
    if school is None:
        school = PrivateSchool(
            name=settings.default_school_name,
            code="NEES",
            motto="Excellence in private education",
        )
        db.add(school)
        db.flush()

    admin = db.scalar(
        select(User).where(User.username == settings.default_admin_username)
    )
    if admin is None:
        admin = User(
            username=settings.default_admin_username,
            email="admin@nees-school.com",
            full_name="System Administrator",
            hashed_password=hash_password(settings.default_admin_password),
            role="admin",
            is_active=True,
            school_id=school.id,
        )
        db.add(admin)

    ui_config = db.scalar(
        select(UiConfig).where(UiConfig.school_id == school.id)
    )
    if ui_config is None:
        db.add(UiConfig(school_id=school.id))

    db.commit()
