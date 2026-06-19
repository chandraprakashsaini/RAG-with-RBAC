from __future__ import annotations

import bcrypt
from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import jwt

from app.core.config import get_settings

_settings = get_settings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def create_access_token(
    subject: UUID | str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=_settings.jwt_expire_minutes)
    )
    to_encode = {
        "sub": str(subject),
        "role": role,
        "exp": expire,
    }
    return jwt.encode(
        to_encode, _settings.jwt_secret, algorithm=_settings.jwt_algorithm
    )


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, _settings.jwt_secret, algorithms=[_settings.jwt_algorithm]
        )
        return payload
    except jwt.JWTError:
        raise ValueError("Invalid token")