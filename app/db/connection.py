from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

_settings = get_settings()

DATABASE_URL = _settings.database_url


class Base(DeclarativeBase):
    pass


def _make_async_url(url: str) -> str:
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///")
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://")
    return url


def _engine_kwargs(url: str) -> dict:
    """Build engine kwargs appropriate for the backend.

    `check_same_thread` is sqlite-only; passing it to asyncpg raises TypeError.
    Pool sizing/pre_ping/recycle apply to non-sqlite backends.
    """
    kwargs: dict = {}
    if url.startswith("sqlite:///"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_pre_ping"] = True
        kwargs["pool_recycle"] = 3600
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 20
    return kwargs


engine = create_async_engine(
    _make_async_url(_settings.database_url),
    echo=_settings.debug,
    **_engine_kwargs(_settings.database_url),
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db():
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()

