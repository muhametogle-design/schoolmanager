"""Pydantic v2 schemas for the management module (schools, students, photos)."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, computed_field, field_validator

from app.schemas.common import EmailMixin, ORMModel

#: Public URL prefixes derived from the ``/static`` mount in ``app.main`` and
#: the storage layout ``<static_root>/uploads/<subdir>/<filename>``.
_AVATAR_URL_BASE = "/static/uploads/avatars"
_LOGO_URL_BASE = "/static/uploads/logos"


class SchoolCreate(EmailMixin):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=2, max_length=24)
    address: str | None = Field(default=None, max_length=255)

    @field_validator("code")
    @classmethod
    def _normalise_code(cls, value: str) -> str:
        return value.strip().upper()


class SchoolRead(ORMModel):
    id: int
    name: str
    code: str
    email: str | None
    address: str | None
    logo_filename: str | None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def logo_url(self) -> str | None:
        if not self.logo_filename:
            return None
        return f"{_LOGO_URL_BASE}/{self.logo_filename}"


class StudentCreate(EmailMixin):
    school_id: int = Field(ge=1)
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    grade_label: str | None = Field(default=None, max_length=32)


class StudentUpdate(EmailMixin):
    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, min_length=1, max_length=80)
    grade_label: str | None = Field(default=None, max_length=32)
    is_active: bool | None = None


class StudentRead(ORMModel):
    id: int
    school_id: int
    first_name: str
    last_name: str
    full_name: str
    email: str | None
    grade_label: str | None
    is_active: bool
    avatar_filename: str | None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def avatar_url(self) -> str | None:
        if not self.avatar_filename:
            return None
        return f"{_AVATAR_URL_BASE}/{self.avatar_filename}"
