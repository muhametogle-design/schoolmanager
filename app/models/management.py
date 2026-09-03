"""Organisation records: schools and students (management module).

The photo columns (``avatar_filename`` / ``logo_filename``) store only the
file name persisted by :class:`app.services.storage.FileStorageService` under
``app/static/uploads/<subdir>/``; public URLs are derived in the schema layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.finance import Invoice


class School(TimestampMixin, Base):
    """A school (tenant) in the NE-ES system."""

    __tablename__ = "schools"
    __table_args__: ClassVar = (UniqueConstraint("code", name="uq_schools_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    #: Short uppercase identifier, normalised by the schema layer.
    code: Mapped[str] = mapped_column(String(24), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254))
    address: Mapped[str | None] = mapped_column(String(255))
    #: Stored file name of the school logo (None until uploaded).
    logo_filename: Mapped[str | None] = mapped_column(String(255))

    students: Mapped[list[Student]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )


class Student(TimestampMixin, Base):
    """A student enrolled at one school."""

    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"), index=True, nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254), unique=True)
    grade_label: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    #: Stored file name of the pupil's avatar photo (None until uploaded).
    avatar_filename: Mapped[str | None] = mapped_column(String(255))

    school: Mapped[School] = relationship(back_populates="students")
    invoices: Mapped[list[Invoice]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
