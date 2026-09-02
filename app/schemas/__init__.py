"""Schema registry - every Pydantic schema is explicitly exported here.

Keep these imports static and explicit: no dynamic loaders, pkgutil
iteration or importlib tricks, which cause circular-import bugs.

Import order matters only for readability: ``auth`` is imported first because
``academics`` references ``UserInfo`` from it. Python resolves that through
``sys.modules`` regardless, but this order keeps the graph obvious.
"""
from app.schemas.academics import (
    ClassCreate,
    SchoolClassResponse,
    SubjectCreate,
    SubjectResponse,
)
from app.schemas.auth import LoginRequest, TokenResponse, UserInfo, UserRole
from app.schemas.management import (
    PhotoUploadRequest,
    SchoolResponse,
    SchoolUiConfig,
    UiConfigBase,
    UiConfigUpdate,
)
from app.schemas.student import StudentCreate, StudentResponse, StudentStatus

__all__ = [
    # auth
    "LoginRequest",
    "TokenResponse",
    "UserInfo",
    "UserRole",
    # academics
    "ClassCreate",
    "SchoolClassResponse",
    "SubjectCreate",
    "SubjectResponse",
    # student
    "StudentCreate",
    "StudentResponse",
    "StudentStatus",
    # management
    "PhotoUploadRequest",
    "SchoolResponse",
    "SchoolUiConfig",
    "UiConfigBase",
    "UiConfigUpdate",
]
