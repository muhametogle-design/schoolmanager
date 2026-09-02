"""Student endpoints: list, create and retrieve student records."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.identity import User
from app.schemas.student import StudentCreate, StudentResponse
from app.services.students import (
    create_student,
    get_student,
    get_student_by_number,
    list_students,
)

router = APIRouter(prefix="/students", tags=["Students"])


@router.get(
    "/",
    response_model=list[StudentResponse],
    summary="List students",
)
def students_list(
    school_id: int | None = Query(
        default=None, description="Filter by school ID (defaults to all schools)."
    ),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[StudentResponse]:
    """Return every student record, optionally filtered by ``school_id``."""
    students = list_students(db, school_id=school_id)
    return [StudentResponse.model_validate(student) for student in students]


@router.post(
    "/",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enrol a new student",
)
def students_create(
    payload: StudentCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> StudentResponse:
    """Enrol a new student and return the created record.

    The ``student_number`` must be unique across the school - a second
    enrolment with the same number is rejected with HTTP 409.
    """
    existing = get_student_by_number(db, payload.student_number)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A student with number '{payload.student_number}' already exists.",
        )
    student = create_student(db, payload.model_dump())
    return StudentResponse.model_validate(student)


@router.get(
    "/{student_id}",
    response_model=StudentResponse,
    summary="Get a student by ID",
)
def students_get(
    student_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> StudentResponse:
    """Return the student with the given ID (404 when not found)."""
    student = get_student(db, student_id)
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with id '{student_id}' was not found.",
        )
    return StudentResponse.model_validate(student)
