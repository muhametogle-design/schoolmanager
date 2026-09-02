"""Management endpoints: UI configuration (colors/branding) and photos."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_optional_current_user
from app.db.session import get_db
from app.models.identity import User
from app.schemas.management import (
    PhotoUploadRequest,
    SchoolResponse,
    SchoolUiConfig,
    UiConfigUpdate,
)
from app.services.management import (
    get_active_school_ui_config,
    get_school,
    store_photo,
    update_school_ui_config,
)

router = APIRouter(prefix="/management", tags=["Management"])


# --------------------------------------------------------------------------
# School UI configuration (colors & branding)
# --------------------------------------------------------------------------
@router.get(
    "/settings",
    response_model=SchoolUiConfig,
    summary="Get the active school UI configuration",
)
def ui_config_get(
    school_code: str | None = Query(
        default=None,
        description="Optional school code to resolve school-specific branding.",
    ),
    db: Session = Depends(get_db),
    _current_user: User | None = Depends(get_optional_current_user),
) -> SchoolUiConfig:
    """Return the active branding/UI configuration.

    The endpoint is public so the front-end can render branding before a
    user signs in. When ``school_code`` is given, branding for that school is
    preferred; otherwise the first active school configuration is returned.
    """
    ui_config = get_active_school_ui_config(db, school_code=school_code)
    if ui_config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No school UI configuration was found. Run the app once to seed it.",
        )

    school = ui_config.school if ui_config.school_id else None
    if school is None and school_code:
        school = get_school(db, school_code=school_code)
    if school is None:
        school = get_school(db)

    response = SchoolUiConfig.model_validate(ui_config)
    if school is not None:
        response.school_id = school.id
        response.school_name = school.name
    return response


@router.put(
    "/settings",
    response_model=SchoolUiConfig,
    summary="Update the school UI configuration",
)
def ui_config_update(
    payload: UiConfigUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> SchoolUiConfig:
    """Partially update the school branding/UI configuration.

    Only the fields present in the request body are changed; colour values
    are validated as ``#RRGGBB`` hex codes by the schema.
    """
    ui_config = update_school_ui_config(db, payload)

    school = ui_config.school if ui_config.school_id else None
    if school is None:
        school = get_school(db)
    response = SchoolUiConfig.model_validate(ui_config)
    if school is not None:
        response.school_id = school.id
        response.school_name = school.name
    return response


@router.get(
    "/settings/school",
    response_model=SchoolResponse,
    summary="Get school profile information",
)
def school_get(
    school_code: str | None = Query(
        default=None, description="Optional school code to look up."
    ),
    db: Session = Depends(get_db),
    _current_user: User | None = Depends(get_optional_current_user),
) -> SchoolResponse:
    """Return the school profile matching ``school_code`` (or the first school)."""
    school = get_school(db, school_code=school_code)
    if school is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No school was found.",
        )
    return SchoolResponse.model_validate(school)


# --------------------------------------------------------------------------
# Photo handling (placeholder)
# --------------------------------------------------------------------------
@router.post(
    "/settings/logo",
    response_model=dict,
    summary="Upload the school logo (placeholder)",
)
def school_logo_upload(
    payload: PhotoUploadRequest,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> dict:
    """Upload the school logo (placeholder implementation).

    The request body must contain a base64-encoded image. The endpoint
    currently returns the target path without persisting the bytes - see
    ``app.services.management.store_photo``.
    """
    if payload.photo_type != "logo":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This endpoint only accepts 'logo' photo_type values.",
        )
    path = store_photo(db, payload)
    return {"status": "accepted", "photo_url": path, "message": "Placeholder: file not stored yet."}


@router.post(
    "/settings/photos",
    response_model=dict,
    summary="Upload a student/school photo (placeholder)",
)
def photo_upload(
    payload: PhotoUploadRequest,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> dict:
    """Upload a photo (placeholder implementation)."""
    path = store_photo(db, payload)
    return {"status": "accepted", "photo_url": path, "message": "Placeholder: file not stored yet."}
