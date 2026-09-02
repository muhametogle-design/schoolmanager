"""Academic-management endpoints: school classes and subjects."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.identity import User
from app.schemas.academics import (
    ClassCreate,
    SchoolClassResponse,
    SubjectCreate,
    SubjectResponse,
)
from app.services.students import (
    create_subject,
    get_school_class,
    get_subject,
    list_school_classes,
    list_subjects,
)

router = APIRouter(prefix="/academics", tags=["Academics"])


# --------------------------------------------------------------------------
# School classes
# --------------------------------------------------------------------------
@router.get(
    "/classes",
    response_model=list[SchoolClassResponse],
    summary="List school classes",
)
def classes_list(
    school_id: int | None = Query(
        default=None, description="Filter by school ID (defaults to all schools)."
    ),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[SchoolClassResponse]:
    """Return every school class, with its teacher and student count."""
    classes = list_school_classes(db, school_id=school_id)
    return [SchoolClassResponse.model_validate(school_class) for school_class in classes]


@router.post(
    "/classes",
    response_model=SchoolClassResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a school class",
)
def classes_create(
    payload: ClassCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> SchoolClassResponse:
    """Create a new school class and return the stored record."""
    from app.models.academics import SchoolClass

    school_class = SchoolClass.from_payload(payload.model_dump())
    db.add(school_class)
    db.commit()
    db.refresh(school_class)
    school_class.student_count = 0  # type: ignore[attr-defined]
    return SchoolClassResponse.model_validate(school_class)


@router.get(
    "/classes/{class_id}",
    response_model=SchoolClassResponse,
    summary="Get a school class by ID",
)
def classes_get(
    class_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> SchoolClassResponse:
    """Return the school class with the given ID (404 when not found)."""
    school_class = get_school_class(db, class_id)
    if school_class is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"School class with id '{class_id}' was not found.",
        )
    return SchoolClassResponse.model_validate(school_class)


# --------------------------------------------------------------------------
# Subjects
# --------------------------------------------------------------------------
@router.get(
    "/subjects",
    response_model=list[SubjectResponse],
    summary="List subjects",
)
def subjects_list(
    school_id: int | None = Query(
        default=None, description="Filter by school ID (defaults to all schools)."
    ),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[SubjectResponse]:
    """Return every subject (optionally filtered by ``school_id``)."""
    subjects = list_subjects(db, school_id=school_id)
    return [SubjectResponse.model_validate(subject) for subject in subjects]


@router.post(
    "/subjects",
    response_model=SubjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a subject",
)
def subjects_create(
    payload: SubjectCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> SubjectResponse:
    """Create a new subject and return the stored record."""
    subject = create_subject(db, payload.model_dump())
    return SubjectResponse.model_validate(subject)


@router.get(
    "/subjects/{subject_id}",
    response_model=SubjectResponse,
    summary="Get a subject by ID",
)
def subjects_get(
    subject_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> SubjectResponse:
    """Return the subject with the given ID (404 when not found)."""
    subject = get_subject(db, subject_id)
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subject with id '{subject_id}' was not found.",
        )
    return SubjectResponse.model_validate(subject)
