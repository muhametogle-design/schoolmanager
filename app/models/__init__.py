"""Model registry - every ORM model is explicitly exported here.

Importing this package registers all model classes on ``Base.metadata`` so
``init_db()`` can create every table. Keep these imports static and explicit:
do not add dynamic loaders, pkgutil iteration or importlib tricks here, they
cause circular-import and registration bugs.
"""
from app.models.academics import SchoolClass, Student, Subject
from app.models.identity import PrivateSchool, User
from app.models.management import UiConfig

__all__ = [
    "PrivateSchool",
    "User",
    "SchoolClass",
    "Student",
    "Subject",
    "UiConfig",
]
