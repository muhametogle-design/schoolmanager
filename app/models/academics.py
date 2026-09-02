"""Academic domain models: classes, students and subjects."""
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids import cycles
    from app.models.identity import PrivateSchool, User
    from app.models.management import UiConfig

# Tracked grade levels, e.g. "Grade 1" .. "Grade 12".
STUDENT_STATUSES = ("active", "inactive", "graduated", "suspended")


class SchoolClass(Base):
    """A grade/class group of a school, e.g. "Grade 5 - A"."""

    __tablename__ = "school_classes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    grade_level: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)
    room: Mapped[str | None] = mapped_column(String(50))
    capacity: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    school_id: Mapped[int | None] = mapped_column(
        ForeignKey("private_schools.id", ondelete="SET NULL"), index=True
    )
    class_teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    school: Mapped["PrivateSchool | None"] = relationship(back_populates="classes")
    class_teacher: Mapped["User | None"] = relationship(
        foreign_keys=[class_teacher_id]
    )
    students: Mapped[list["Student"]] = relationship(
        back_populates="school_class", cascade="all, delete-orphan"
    )
    subjects: Mapped[list["Subject"]] = relationship(
        back_populates="school_class", cascade="all, delete-orphan"
    )

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "SchoolClass":
        """Build an instance from a validated payload dict (schema ``.model_dump()``)."""
        fields = cls.__table__.columns.keys() & payload.keys()
        return cls(**{field: payload[field] for field in fields})


class Student(Base):
    """A student enrolled in a school class."""

    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    student_number: Mapped[str] = mapped_column(
        String(30), unique=True, index=True, nullable=False
    )
    gender: Mapped[str | None] = mapped_column(String(20))
    birth_date: Mapped[date | None] = mapped_column(Date)
    email: Mapped[str | None] = mapped_column(String(120), index=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    address: Mapped[str | None] = mapped_column(String(255))
    guardian_name: Mapped[str | None] = mapped_column(String(150))
    guardian_phone: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False, index=True
    )
    photo_path: Mapped[str | None] = mapped_column(String(500))
    enrollment_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    school_id: Mapped[int | None] = mapped_column(
        ForeignKey("private_schools.id", ondelete="SET NULL"), index=True
    )
    class_id: Mapped[int | None] = mapped_column(
        ForeignKey("school_classes.id", ondelete="SET NULL"), index=True
    )

    school: Mapped["PrivateSchool | None"] = relationship(back_populates="students")
    school_class: Mapped["SchoolClass | None"] = relationship(
        back_populates="students", foreign_keys=[class_id]
    )
    user_account: Mapped["User | None"] = relationship(
        back_populates="student", uselist=False
    )
    ui_config: Mapped["UiConfig | None"] = relationship(
        back_populates="student", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        """Convenience property: ``"{first_name} {last_name}"``."""
        return f"{self.first_name} {self.last_name}".strip()

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "Student":
        """Build an instance from a validated payload dict (schema ``.model_dump()``)."""
        fields = cls.__table__.columns.keys() & payload.keys()
        return cls(**{field: payload[field] for field in fields})


class Subject(Base):
    """A subject that can be taught to one or more classes."""

    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str | None] = mapped_column(String(20), index=True)
    description: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    school_id: Mapped[int | None] = mapped_column(
        ForeignKey("private_schools.id", ondelete="SET NULL"), index=True
    )
    class_id: Mapped[int | None] = mapped_column(
        ForeignKey("school_classes.id", ondelete="SET NULL"), index=True
    )
    teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    school: Mapped["PrivateSchool | None"] = relationship(back_populates="subjects")
    school_class: Mapped["SchoolClass | None"] = relationship(
        back_populates="subjects", foreign_keys=[class_id]
    )
    teacher: Mapped["User | None"] = relationship(foreign_keys=[teacher_id])

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "Subject":
        """Build an instance from a validated payload dict (schema ``.model_dump()``)."""
        fields = cls.__table__.columns.keys() & payload.keys()
        return cls(**{field: payload[field] for field in fields})
