"""Password hashing (PBKDF2-HMAC-SHA256) and JWT access-token helpers."""
import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.core.config import settings

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 240_000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    """Hash a plain-text password using PBKDF2-HMAC-SHA256.

    The encoded value embeds algorithm, iterations and salt so that
    ``verify_password`` needs no extra state:

        pbkdf2_sha256$240000$<salt_b64>$<digest_b64>
    """
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return "$".join(
        [
            _ALGORITHM,
            str(_ITERATIONS),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        ]
    )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a PBKDF2 encoded hash."""
    try:
        algorithm, iterations_str, salt_b64, digest_b64 = hashed_password.split("$")
        iterations = int(iterations_str)
        salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_b64.encode("ascii"))
    except (ValueError, TypeError):
        return False

    if algorithm != _ALGORITHM or iterations < 1:
        return False

    actual = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def create_access_token(
    subject: int | str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token for the given user."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.token_algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT access token.

    Returns the token payload when the token is valid, ``None`` otherwise
    (expired, malformed or signed with a different key).
    """
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.token_algorithm])
    except jwt.PyJWTError:
        return None
