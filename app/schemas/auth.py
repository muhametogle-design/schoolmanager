"""Authentication-related Pydantic schemas."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

UserRole = Literal["admin", "teacher", "student", "finance"]


class LoginRequest(BaseModel):
    """Credentials accepted by ``POST /auth/login``."""

    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)

    model_config = ConfigDict(
        json_schema_extra={"example": {"username": "admin", "password": "admin123"}}
    )


class TokenResponse(BaseModel):
    """Successful login result."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(
        description="Token lifetime in seconds (0 when not available)"
    )
    user: "UserInfo"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIs...",
                "token_type": "bearer",
                "expires_in": 86400,
                "user": {
                    "id": 1,
                    "username": "admin",
                    "full_name": "System Administrator",
                    "email": "admin@nees-school.com",
                    "role": "admin",
                    "school_id": 1,
                },
            }
        }
    )


class UserInfo(BaseModel):
    """Safe user representation (no credentials) returned to the client."""

    id: int
    username: str
    full_name: str | None = None
    email: EmailStr | None = None
    role: UserRole
    phone: str | None = None
    is_active: bool = True
    school_id: int | None = None
    last_login_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# Forward reference so TokenResponse can reference UserInfo defined after it.
TokenResponse.model_rebuild()
