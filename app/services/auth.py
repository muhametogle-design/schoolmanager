"""Authentication and user-account services."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.identity import User


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """Return the user when the credentials match, ``None`` otherwise.

    Looks the user up by username OR email so both identifiers can be used
    to sign in. A user that is not active never authenticates.
    """
    user = db.scalar(
        select(User).where(
            (User.username == username) | (User.email == username)
        )
    )
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
