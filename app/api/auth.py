"""Authentication endpoints: login and current-user profile."""
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.identity import User
from app.schemas.auth import LoginRequest, TokenResponse, UserInfo
from app.services.auth import authenticate_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate with username/email and password",
)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    """Exchange valid credentials for a JWT access token.

    A 401 is returned for unknown users, wrong passwords and disabled
    accounts. On success, ``last_login_at`` is updated on the user record.
    """
    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.last_login_at = datetime.now(UTC)
    db.commit()
    db.refresh(user)

    expires_in = settings.access_token_expire_minutes * 60
    token = create_access_token(subject=user.id, role=user.role)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserInfo.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserInfo,
    summary="Return the profile of the authenticated user",
)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserInfo:
    """Return the profile of the currently authenticated user (token required)."""
    return UserInfo.model_validate(current_user)
