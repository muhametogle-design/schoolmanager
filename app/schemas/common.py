"""Shared Pydantic v2 schema primitives."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ORMModel(BaseModel):
    """Base class for read schemas: constructible via ``model_validate(orm_obj)``."""

    model_config = ConfigDict(from_attributes=True)


class EmailMixin(BaseModel):
    """Optional e-mail field with a lightweight format check.

    Kept dependency-free on purpose (no ``email-validator``); tighten by
    swapping in ``pydantic.EmailStr`` if stricter validation is required.
    """

    email: str | None = Field(default=None, max_length=254)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str | None) -> str | None:
        if value is not None and "@" not in value:
            raise ValueError("must be a valid email address")
        return value
