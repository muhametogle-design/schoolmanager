"""Management domain models: per-school / per-student UI configuration."""
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids import cycles
    from app.models.academics import Student
    from app.models.identity import PrivateSchool

# CSS colour values that are allowed in the UI configuration.
ALLOWED_COLORS = (
    "#000000",
    "#FFFFFF",
    "#FF0000",
    "#00FF00",
    "#0000FF",
    "#FFFF00",
    "#00FFFF",
    "#FF00FF",
    "#C0C0C0",
    "#808080",
    "#800000",
    "#808000",
    "#008000",
    "#800080",
    "#008080",
    "#000080",
    "#FFA500",
    "#FFC0CB",
    "#A52A2A",
    "#EE82EE",
    "#F5F5DC",
    "#FAEBD7",
    "#FFFFFF",
)


class UiConfig(Base):
    """Branding / colour configuration for the front-end UI.

    A config row exists per school (global branding). When a student supplies
    their own school code on a photo upload, a student-scoped override can be
    stored and is returned ahead of the school-level config.
    """

    __tablename__ = "ui_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    school_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    primary_color: Mapped[str] = mapped_column(
        String(7), default="#2563EB", nullable=False
    )
    secondary_color: Mapped[str] = mapped_column(
        String(7), default="#F59E0B", nullable=False
    )
    background_color: Mapped[str] = mapped_column(
        String(7), default="#F3F4F6", nullable=False
    )
    text_color: Mapped[str] = mapped_column(
        String(7), default="#111827", nullable=False
    )
    logo_url: Mapped[str | None] = mapped_column(String(500))
    custom_css: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )  # "1" matches legacy boolean serialisation
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    school_id: Mapped[int | None] = mapped_column(
        ForeignKey("private_schools.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[int | None] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True
    )

    school: Mapped["PrivateSchool | None"] = relationship(back_populates="ui_config")
    student: Mapped["Student | None"] = relationship(back_populates="ui_config")

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "UiConfig":
        """Build an instance from a validated payload dict (schema ``.model_dump()``)."""
        fields = cls.__table__.columns.keys() & payload.keys()
        return cls(**{field: payload[field] for field in fields})
