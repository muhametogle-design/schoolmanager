"""Management services: school branding / UI configuration and photos."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.identity import PrivateSchool
from app.models.management import UiConfig
from app.schemas.management import PhotoUploadRequest, UiConfigUpdate


def get_school(db: Session, school_code: str | None = None) -> PrivateSchool | None:
    """Return the school matching ``school_code`` or the first one available."""
    if school_code:
        school = db.scalar(
            select(PrivateSchool).where(PrivateSchool.code == school_code)
        )
        if school is not None:
            return school
    return db.scalar(select(PrivateSchool).order_by(PrivateSchool.id).limit(1))


def get_active_school_ui_config(db: Session, school_code: str | None = None) -> UiConfig | None:
    """Resolve the active UI configuration for a school.

    Resolution order:
      1. a school whose ``code`` equals ``school_code`` (case-insensitive)
         and that has an active config row;
      2. the first active school-level config row.

    Callers that need the school name attach ``ui.school`` beforehand.
    """
    query = (
        select(UiConfig)
        .where(UiConfig.is_active == 1)
        .order_by(UiConfig.id)
        .limit(1)
    )
    if school_code:
        ui = db.scalar(
            select(UiConfig)
            .join(PrivateSchool, PrivateSchool.id == UiConfig.school_id)
            .where(
                UiConfig.is_active == 1,
                PrivateSchool.code.ilike(school_code),
            )
            .limit(1)
        )
        if ui is not None:
            return ui
    return db.scalar(query)


def update_school_ui_config(db: Session, data: UiConfigUpdate) -> UiConfig:
    """Apply a partial UI-config update and persist it.

    Only fields explicitly present in the request are written
    (``model_dump(exclude_unset=True)``); colours and booleans were already
    normalised by the Pydantic schema. Falls back to a fresh row when no
    school config exists yet.
    """
    ui_config = get_active_school_ui_config(db)
    if ui_config is None:
        ui_config = UiConfig(school_id=getattr(get_school(db), "id", None))
        db.add(ui_config)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ui_config, field, value)

    db.commit()
    db.refresh(ui_config)
    return ui_config


def store_photo(db: Session, payload: PhotoUploadRequest) -> str:
    """Persist an uploaded photo and return its public URL/path.

    Placeholder implementation: it only derives the target path and returns
    it. Replace the body with real storage (S3, a local ``uploads/`` folder,
    ...) in production - keeping storage here keeps the API routers thin.
    """
    # TODO(implementation): decode the base64 payload and write the image file.
    photo_kind = "logo" if payload.photo_type == "logo" else "student"
    reference = payload.student_id or payload.school_code or "default"
    return f"/uploads/{photo_kind}-{reference}.jpg"
