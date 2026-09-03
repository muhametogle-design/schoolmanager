"""Management service: schools, students, and photo/logo uploads.

This replaces the placeholder-only scaffold implementation: avatars and school
logos are now written to disk through :class:`~app.services.storage.FileStorageService`
under ``app/static/uploads/``, previous files are cleaned up on replacement,
and the DB stores only the generated file name.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ServiceError
from app.models.management import School, Student
from app.schemas.management import SchoolCreate, StudentCreate, StudentUpdate
from app.services.storage import FileStorageService

_AVATAR_SUBDIR = "avatars"
_LOGO_SUBDIR = "logos"


class ManagementService:
    def __init__(self, session: Session, storage: FileStorageService) -> None:
        self._session = session
        self._storage = storage

    # -- schools ---------------------------------------------------------

    def create_school(self, payload: SchoolCreate) -> School:
        existing = self._session.scalar(select(School.id).where(School.code == payload.code))
        if existing is not None:
            raise ServiceError(f"school code {payload.code!r} is already in use")
        school = School(**payload.model_dump())
        self._session.add(school)
        self._session.commit()
        return school

    def list_schools(self) -> Sequence[School]:
        return self._session.scalars(select(School).order_by(School.id)).all()

    def get_school(self, school_id: int) -> School:
        school = self._session.get(School, school_id)
        if school is None:
            raise NotFoundError(f"school {school_id} not found")
        return school

    # -- students ----------------------------------------------------------

    def create_student(self, payload: StudentCreate) -> Student:
        self.get_school(payload.school_id)  # 404 when the school does not exist
        if payload.email is not None and self._email_taken(payload.email):
            raise ServiceError(f"email {payload.email!r} is already assigned to a student")
        student = Student(**payload.model_dump())
        self._session.add(student)
        self._session.commit()
        return student

    def get_student(self, student_id: int) -> Student:
        student = self._session.get(Student, student_id)
        if student is None:
            raise NotFoundError(f"student {student_id} not found")
        return student

    def list_students(self, school_id: int | None = None) -> Sequence[Student]:
        stmt = select(Student).order_by(Student.id)
        if school_id is not None:
            self.get_school(school_id)  # 404 signal for an unknown filter
            stmt = stmt.where(Student.school_id == school_id)
        return self._session.scalars(stmt).all()

    def update_student(self, student_id: int, payload: StudentUpdate) -> Student:
        student = self.get_student(student_id)
        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            raise ServiceError("no fields to update")
        email = changes.get("email")
        if email is not None:
            taken = self._session.scalar(
                select(Student.id).where(Student.email == email, Student.id != student_id)
            )
            if taken is not None:
                raise ServiceError(f"email {email!r} is already assigned to a student")
        for field, value in changes.items():
            setattr(student, field, value)
        self._session.commit()
        return student

    # -- student avatars ----------------------------------------------------

    def set_student_avatar(
        self, student_id: int, *, data: bytes, content_type: str | None
    ) -> Student:
        student = self.get_student(student_id)
        stored = self._storage.save_image(
            subdir=_AVATAR_SUBDIR,
            data=data,
            declared_content_type=content_type,
            prefix=f"student-{student_id}",
        )
        previous = student.avatar_filename
        student.avatar_filename = stored.filename
        self._session.commit()
        if previous:
            # Best-effort cleanup of the replaced file; the DB is authoritative.
            self._storage.delete(subdir=_AVATAR_SUBDIR, filename=previous)
        return student

    def remove_student_avatar(self, student_id: int) -> Student:
        student = self.get_student(student_id)
        if student.avatar_filename:
            self._storage.delete(subdir=_AVATAR_SUBDIR, filename=student.avatar_filename)
            student.avatar_filename = None
            self._session.commit()
        return student

    # -- school logos -------------------------------------------------------

    def set_school_logo(self, school_id: int, *, data: bytes, content_type: str | None) -> School:
        school = self.get_school(school_id)
        stored = self._storage.save_image(
            subdir=_LOGO_SUBDIR,
            data=data,
            declared_content_type=content_type,
            prefix=f"school-{school_id}",
        )
        previous = school.logo_filename
        school.logo_filename = stored.filename
        self._session.commit()
        if previous:
            self._storage.delete(subdir=_LOGO_SUBDIR, filename=previous)
        return school

    def remove_school_logo(self, school_id: int) -> School:
        school = self.get_school(school_id)
        if school.logo_filename:
            self._storage.delete(subdir=_LOGO_SUBDIR, filename=school.logo_filename)
            school.logo_filename = None
            self._session.commit()
        return school

    # -- helpers -----------------------------------------------------------

    def _email_taken(self, email: str) -> bool:
        return (
            self._session.scalar(select(Student.id).where(Student.email == email)) is not None
        )
