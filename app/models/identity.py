"""Identity domain models: schools and users."""
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids import cycles
    from app.models.academics import SchoolClass, Student, Subject
    from app.models.management import UiConfig

# Allowed user roles inside the system.
USER_ROLES = ("admin", "teacher", "student", "finance")


class PrivateSchool(Base):
    """A private school that owns the system's data (multi-tenant anchor)."""

    __tablename__ = "private_schools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )
    address: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(120))
    motto: Mapped[str | None] = mapped_column(String(255))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    users: Mapped[list["User"]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )
    students: Mapped[list["Student"]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )
    classes: Mapped[list["SchoolClass"]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )
    subjects: Mapped[list["Subject"]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )
    ui_config: Mapped["UiConfig | None"] = relationship(
        back_populates="school", uselist=False, cascade="all, delete-orphan"
    )

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "PrivateSchool":
        """Build an instance from a validated payload dict (schema ``.model_dump()``)."""
        fields = cls.__table__.columns.keys() & payload.keys()
        return cls(**{field: payload[field] for field in fields})


class User(Base):
    """A user account (admin, teacher, student or finance staff)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    email: Mapped[str | None] = mapped_column(String(120), index=True)
    full_name: Mapped[str | None] = mapped_column(String(150))
    role: Mapped[str] = mapped_column(
        String(20), default="student", nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    school_id: Mapped[int | None] = mapped_column(
        ForeignKey("private_schools.id", ondelete="SET NULL"), index=True
    )
    student_id: Mapped[int | None] = mapped_column(
        ForeignKey("students.id", ondelete="SET NULL"), index=True
    )

    school: Mapped["PrivateSchool | None"] = relationship(back_populates="users")
    student: Mapped["Student | None"] = relationship(back_populates="user_account")

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "User":
        """Build an instance from a validated payload dict (schema ``.model_dump()``)."""
        fields = cls.__table__.columns.keys() & payload.keys()
        return cls(**{field: payload[field] for field in fields})
