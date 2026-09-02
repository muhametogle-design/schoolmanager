"""Student and academic-record services (class/subject operations)."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.academics import SchoolClass, Student, Subject


def list_school_classes(db: Session, school_id: int | None = None) -> list[SchoolClass]:
    """Return all classes, optionally filtered by school, with a student count.

    ``student_count`` is attached dynamically so the schema can serialise it
    from a plain ORM object (an ephemeral attribute is enough).
    """
    count_stmt = (
        select(Student.class_id, func.count(Student.id).label("count"))
        .group_by(Student.class_id)
        .subquery()
    )
    query = (
        select(SchoolClass, count_stmt.c.count)
        .outerjoin(count_stmt, count_stmt.c.class_id == SchoolClass.id)
        .order_by(SchoolClass.name)
    )
    if school_id is not None:
        query = query.where(SchoolClass.school_id == school_id)

    classes: list[SchoolClass] = []
    for row in db.execute(query):
        school_class: SchoolClass = row[0]
        school_class.student_count = row[1] or 0  # type: ignore[attr-defined]
        classes.append(school_class)
    return classes


def get_school_class(db: Session, class_id: int) -> SchoolClass | None:
    """Return a single class with its teacher and populated student count."""
    school_class = db.get(SchoolClass, class_id)
    if school_class is None:
        return None
    school_class.student_count = db.scalar(  # type: ignore[attr-defined]
        select(func.count(Student.id)).where(Student.class_id == class_id)
    ) or 0
    return school_class


def list_students(db: Session, school_id: int | None = None) -> list[Student]:
    """Return all students, optionally filtered by school."""
    query = select(Student).order_by(Student.last_name, Student.first_name)
    if school_id is not None:
        query = query.where(Student.school_id == school_id)
    return list(db.scalars(query))


def get_student(db: Session, student_id: int) -> Student | None:
    """Return a single student by id."""
    return db.get(Student, student_id)


def get_student_by_number(db: Session, student_number: str) -> Student | None:
    """Look up a student by their (unique) admission number."""
    return db.scalar(select(Student).where(Student.student_number == student_number))


def create_student(db: Session, data: dict) -> Student:
    """Create and commit a new student record."""
    student = Student.from_payload(data)
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


def list_subjects(db: Session, school_id: int | None = None) -> list[Subject]:
    """Return all subjects, optionally filtered by school."""
    query = select(Subject).order_by(Subject.name)
    if school_id is not None:
        query = query.where(Subject.school_id == school_id)
    return list(db.scalars(query))


def get_subject(db: Session, subject_id: int) -> Subject | None:
    """Return a single subject by id."""
    return db.get(Subject, subject_id)


def create_subject(db: Session, data: dict) -> Subject:
    """Create and commit a new subject record."""
    subject = Subject.from_payload(data)
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject
