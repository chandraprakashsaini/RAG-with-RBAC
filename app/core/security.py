from __future__ import annotations

import asyncio
import bcrypt
from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import jwt

from app.core.config import get_settings

_settings = get_settings()

# Precomputed dummy hash so verify_password can always run a constant-time
# bcrypt comparison even when the user is not found, preventing timing attacks
# that would otherwise let an attacker enumerate valid email addresses.
_DUMMY_HASH = bcrypt.hashpw(b"dummy-password-for-timing", bcrypt.gensalt()).decode("utf-8")


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


async def verify_password_async(plain_password: str, hashed_password: str) -> bool:
    return await asyncio.to_thread(verify_password, plain_password, hashed_password)


async def get_password_hash_async(password: str) -> str:
    return await asyncio.to_thread(get_password_hash, password)


async def verify_password_or_dummy_async(
    plain_password: str, hashed_password: str | None
) -> bool:
    """Always run a bcrypt compare (constant time) regardless of whether the
    user exists. Returns False when the user is missing."""
    actual = hashed_password if hashed_password is not None else _DUMMY_HASH
    return await asyncio.to_thread(verify_password, plain_password, actual)


def create_access_token(
    subject: UUID | str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=_settings.jwt_expire_minutes))
    to_encode = {
        "sub": str(subject),
        "role": role,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(
        to_encode, _settings.jwt_secret, algorithm=_settings.jwt_algorithm
    )


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            _settings.jwt_secret,
            algorithms=[_settings.jwt_algorithm],
        )
        return payload
    except jwt.JWTError:
        raise ValueError("Invalid token")