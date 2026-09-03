"""Academic-management Pydantic schemas (classes and subjects)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.auth import UserInfo


class ClassCreate(BaseModel):
    """Payload for creating a school class."""

    name: str = Field(min_length=1, max_length=120)
    grade_level: str = Field(default="", max_length=30)
    academic_year: str = Field(min_length=4, max_length=20)
    room: str | None = Field(default=None, max_length=50)
    capacity: int | None = Field(default=None, ge=1)
    school_id: int | None = None
    class_teacher_id: int | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Grade 5 - A",
                "grade_level": "Grade 5",
                "academic_year": "2026/2027",
                "room": "Room 201",
                "capacity": 30,
            }
        }
    )


class SchoolClassResponse(BaseModel):
    """Class summary without the full student roster."""

    id: int
    name: str
    grade_level: str
    academic_year: str
    room: str | None = None
    capacity: int | None = None
    is_active: bool = True
    school_id: int | None = None
    class_teacher_id: int | None = None
    class_teacher: UserInfo | None = None
    student_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubjectCreate(BaseModel):
    """Payload for creating a subject."""

    name: str = Field(min_length=1, max_length=120)
    code: str | None = Field(default=None, max_length=20)
    description: str | None = Field(default=None, max_length=500)
    school_id: int | None = None
    class_id: int | None = None
    teacher_id: int | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"name": "Mathematics", "code": "MATH", "class_id": 1}
        }
    )


class SubjectResponse(BaseModel):
    """Subject record as returned by the API."""

    id: int
    name: str
    code: str | None = None
    description: str | None = None
    is_active: bool = True
    school_id: int | None = None
    class_id: int | None = None
    teacher_id: int | None = None
    teacher: UserInfo | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
