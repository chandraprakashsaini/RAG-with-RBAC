import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers, setup_logging
from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router
from app.routes.chunking import router as chunking_router
from app.routes.documents import router as documents_router
from app.routes.health import router as health_router

_settings = get_settings()

setup_logging()

_HERE = os.path.dirname(os.path.abspath(__file__))
_FRONTEND_DIR = os.path.join(_HERE, "..", "..", "frontend")


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except Exception:
            return await super().get_response("index.html", scope)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from uuid import UUID

    from app.core.security import get_password_hash
    from app.db.connection import AsyncSessionLocal, Base, engine
    from app.db.models import User, UserRole

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        existing = await session.execute(select(UserRole).limit(1))
        if existing.scalar_one_or_none() is None:
            role_ids = {
                "admin": UUID("11111111-1111-1111-1111-111111111111"),
                "analyst": UUID("22222222-2222-2222-2222-222222222222"),
                "manager": UUID("33333333-3333-3333-3333-333333333333"),
                "executive": UUID("44444444-4444-4444-4444-444444444444"),
                "viewer": UUID("55555555-5555-5555-5555-555555555555"),
            }
            user_ids = {
                "alice": UUID("aaaaaaaa-1111-1111-1111-111111111111"),
                "bob": UUID("bbbbbbbb-2222-2222-2222-222222222222"),
                "carol": UUID("cccccccc-3333-3333-3333-333333333333"),
                "dave": UUID("dddddddd-4444-4444-4444-444444444444"),
                "eve": UUID("eeeeeeee-5555-5555-5555-555555555555"),
            }

            roles = [
                UserRole(id=role_ids["admin"], name="admin", description="Full system access"),
                UserRole(id=role_ids["analyst"], name="analyst", description="Can analyze and query documents"),
                UserRole(id=role_ids["manager"], name="manager", description="Team-level management access"),
                UserRole(id=role_ids["executive"], name="executive", description="Leadership-level access"),
                UserRole(id=role_ids["viewer"], name="viewer", description="Read-only constrained access"),
            ]
            session.add_all(roles)
            await session.flush()

            password = get_password_hash("password123")
            users = [
                User(id=user_ids["alice"], email="alice@example.com", full_name="Alice Admin", password_hash=password, role_id=role_ids["admin"]),
                User(id=user_ids["bob"], email="bob@example.com", full_name="Bob Analyst", password_hash=password, role_id=role_ids["analyst"]),
                User(id=user_ids["carol"], email="carol@example.com", full_name="Carol Manager", password_hash=password, role_id=role_ids["manager"]),
                User(id=user_ids["dave"], email="dave@example.com", full_name="Dave Executive", password_hash=password, role_id=role_ids["executive"]),
                User(id=user_ids["eve"], email="eve@example.com", full_name="Eve Viewer", password_hash=password, role_id=role_ids["viewer"]),
            ]
            session.add_all(users)
            await session.commit()

    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=_settings.app_name,
        version=_settings.app_version,
        debug=_settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(chunking_router, prefix="/api/v1")
    app.include_router(documents_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")

    if os.path.isdir(_FRONTEND_DIR):
        app.mount("/", SPAStaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")

    return app

