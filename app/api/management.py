"""Management API: schools, students, and avatar/logo uploads.

Upload endpoints accept ``multipart/form-data`` with a single ``file`` field.
Raw bytes are handed to the service layer, which validates (magic bytes,
size) and persists them under ``app/static/uploads/``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Query, UploadFile

from app.api.deps import ManagementServiceDep, StorageDep
from app.schemas.management import (
    SchoolCreate,
    SchoolRead,
    StudentCreate,
    StudentRead,
    StudentUpdate,
)

router = APIRouter(prefix="/management", tags=["management"])

SchoolFile = Annotated[UploadFile, File(description="PNG/JPEG/WebP/GIF image upload")]


async def _read_upload(file: UploadFile, limit_bytes: int) -> bytes:
    """Read at most ``limit_bytes`` + 1 so oversize bodies are rejected early."""
    try:
        return await file.read(limit_bytes + 1)
    finally:
        await file.close()


# -- schools ---------------------------------------------------------------


@router.post("/schools", response_model=SchoolRead, status_code=201)
def create_school(payload: SchoolCreate, service: ManagementServiceDep) -> SchoolRead:
    return SchoolRead.model_validate(service.create_school(payload))


@router.get("/schools", response_model=list[SchoolRead])
def list_schools(service: ManagementServiceDep) -> list[SchoolRead]:
    return [SchoolRead.model_validate(school) for school in service.list_schools()]


@router.get("/schools/{school_id}", response_model=SchoolRead)
def get_school(school_id: int, service: ManagementServiceDep) -> SchoolRead:
    return SchoolRead.model_validate(service.get_school(school_id))


@router.post("/schools/{school_id}/logo", response_model=SchoolRead)
async def upload_school_logo(
    school_id: int,
    file: SchoolFile,
    service: ManagementServiceDep,
    storage: StorageDep,
) -> SchoolRead:
    data = await _read_upload(file, storage.max_bytes)
    school = service.set_school_logo(school_id, data=data, content_type=file.content_type)
    return SchoolRead.model_validate(school)


@router.delete("/schools/{school_id}/logo", response_model=SchoolRead)
def remove_school_logo(school_id: int, service: ManagementServiceDep) -> SchoolRead:
    return SchoolRead.model_validate(service.remove_school_logo(school_id))


# -- students ----------------------------------------------------------------


@router.post("/students", response_model=StudentRead, status_code=201)
def create_student(payload: StudentCreate, service: ManagementServiceDep) -> StudentRead:
    return StudentRead.model_validate(service.create_student(payload))


@router.get("/students", response_model=list[StudentRead])
def list_students(
    service: ManagementServiceDep,
    school_id: Annotated[int | None, Query(ge=1)] = None,
) -> list[StudentRead]:
    return [StudentRead.model_validate(s) for s in service.list_students(school_id)]


@router.get("/students/{student_id}", response_model=StudentRead)
def get_student(student_id: int, service: ManagementServiceDep) -> StudentRead:
    return StudentRead.model_validate(service.get_student(student_id))


@router.patch("/students/{student_id}", response_model=StudentRead)
def update_student(
    student_id: int, payload: StudentUpdate, service: ManagementServiceDep
) -> StudentRead:
    return StudentRead.model_validate(service.update_student(student_id, payload))


@router.post("/students/{student_id}/avatar", response_model=StudentRead)
async def upload_student_avatar(
    student_id: int,
    file: SchoolFile,
    service: ManagementServiceDep,
    storage: StorageDep,
) -> StudentRead:
    data = await _read_upload(file, storage.max_bytes)
    student = service.set_student_avatar(student_id, data=data, content_type=file.content_type)
    return StudentRead.model_validate(student)


@router.delete("/students/{student_id}/avatar", response_model=StudentRead)
def remove_student_avatar(student_id: int, service: ManagementServiceDep) -> StudentRead:
    return StudentRead.model_validate(service.remove_student_avatar(student_id))
