"""Management-related Pydantic schemas (UI branding + photo uploads)."""
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


class UiConfigBase(BaseModel):
    """Fields shared by school branding / UI configuration objects."""

    school_name: str | None = Field(default=None, max_length=255)
    primary_color: str | None = None
    secondary_color: str | None = None
    background_color: str | None = None
    text_color: str | None = None
    logo_url: str | None = Field(default=None, max_length=500)
    custom_css: str | None = None
    is_active: bool | int | None = None

    @field_validator(
        "primary_color",
        "secondary_color",
        "background_color",
        "text_color",
        mode="before",
    )
    @classmethod
    def _normalize_color(cls, value: object) -> object:
        """Normalise a colour to uppercase ``#RRGGBB`` and validate it."""
        if value is None or value == "":
            return None
        color = str(value).strip().upper()
        if not HEX_COLOR_PATTERN.match(color):
            raise ValueError(
                f"Invalid color '{value}'. Expected a hex value like '#2563EB'."
            )
        return color


class SchoolUiConfig(BaseModel):
    """UI configuration (colors & branding) as read by the front-end.

    ``school_name`` mirrors the school's public name so the header/branding
    can be rendered from a single object.
    """

    school_id: int | None = None
    student_id: int | None = None
    school_name: str | None = None
    primary_color: str = "#2563EB"
    secondary_color: str = "#F59E0B"
    background_color: str = "#F3F4F6"
    text_color: str = "#111827"
    logo_url: str | None = None
    custom_css: str | None = None
    is_active: bool = True
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UiConfigUpdate(UiConfigBase):
    """Partial update payload for the school UI configuration."""


class PhotoUploadRequest(BaseModel):
    """Payload for the (placeholder) student photo upload endpoint.

    The ``photo`` is accepted as a base64-encoded data URI or a raw base64
    string (``data:image/...;base64,...`` or bare base64). Validation only
    checks the envelope; decoding/storage is handled by the service layer.
    """

    photo: str = Field(min_length=1, description="Base64 image data or data URI.")
    photo_type: Literal["student", "logo"] = "student"
    school_code: str | None = Field(
        default=None,
        max_length=20,
        description="Used to resolve student-specific branding if provided.",
    )
    student_id: int | None = None

    @field_validator("photo", mode="after")
    @classmethod
    def _validate_photo_payload(cls, value: str) -> str:
        """Reject obviously non-image / non-base64 photo payloads early."""
        data = value
        if data.startswith("data:"):  # data URI -> strip the header
            try:
                header, payload = data.split(",", 1)
            except ValueError as exc:  # pragma: no cover - defensive
                raise ValueError("Malformed photo data URI.") from exc
            if not header.startswith("data:image/"):
                raise ValueError("Photo must be an image (data:image/...).")
            data = payload
        if not data or not re.fullmatch(r"[A-Za-z0-9+/=\s]+", data):
            raise ValueError("Photo must be valid base64 data.")
        return value

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "photo": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB...",
                "photo_type": "student",
                "school_code": "NEES",
                "student_id": 1,
            }
        }
    )


class SchoolResponse(BaseModel):
    """School record returned by the management endpoints."""

    id: int
    name: str
    code: str
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    motto: str | None = None
    logo_url: str | None = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
