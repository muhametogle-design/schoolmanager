"""Shared API dependencies: current-user resolution and role guards."""
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.identity import User

# Mark protected routes as bearer-auth secured in the OpenAPI docs. The
# ``auto_error=False`` variant lets us return a uniform 401 ourselves.
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="JWT access token obtained from POST /auth/login",
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve and return the authenticated user or raise HTTP 401."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_optional_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User | None:
    """Resolve the current user when a valid token is supplied, else ``None``.

    Used by public endpoints that personalise their response (e.g. per-user
    branding) without requiring authentication.
    """
    authorization = request.headers.get("Authorization")
    if authorization and authorization.lower().startswith("bearer "):
        payload = decode_access_token(authorization[7:].strip())
        if payload is not None and "sub" in payload:
            try:
                user_id = int(payload["sub"])
            except (TypeError, ValueError):
                return None
            user = db.get(User, user_id)
            if user is not None and user.is_active:
                return user
    return None


def require_roles(*roles: str) -> callable:
    """Return a dependency factory that allows only the given roles."""

    def _role_guard(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of the roles: {', '.join(roles)}",
            )
        return user

    return _role_guard
