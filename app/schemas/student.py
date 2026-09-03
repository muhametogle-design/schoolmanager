"""Student-related Pydantic schemas."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

StudentStatus = Literal["active", "inactive", "graduated", "suspended"]


class StudentCreate(BaseModel):
    """Payload for creating / enrolling a student."""

    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    student_number: str = Field(
        min_length=1,
        max_length=30,
        description="Unique admission number, e.g. 'NEES-2026-001'.",
    )
    gender: Literal["male", "female", "other"] | None = None
    birth_date: date | None = None
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=255)
    guardian_name: str | None = Field(default=None, max_length=150)
    guardian_phone: str | None = Field(default=None, max_length=30)
    class_id: int | None = None
    school_id: int | None = None
    status: StudentStatus = "active"
    enrollment_date: date | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "student_number": "NEES-2026-001",
                "gender": "male",
                "birth_date": "2010-05-12",
                "class_id": 1,
                "enrollment_date": "2026-09-01",
            }
        }
    )


class StudentResponse(BaseModel):
    """Full student record returned by the API."""

    id: int
    first_name: str
    last_name: str
    student_number: str
    gender: str | None = None
    birth_date: date | None = None
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None
    guardian_name: str | None = None
    guardian_phone: str | None = None
    status: StudentStatus = "active"
    class_id: int | None = None
    school_id: int | None = None
    photo_path: str | None = None
    enrollment_date: date | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
