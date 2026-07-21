import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers, setup_logging
from app.core.limiter import HAS_SLOWAPI, limiter
from app.routes.auth import router as auth_router, user_router
from app.routes.chat import router as chat_router
from app.routes.chunking import router as chunking_router
from app.routes.documents import router as documents_router
from app.routes.health import router as health_router

_settings = get_settings()

setup_logging()

_HERE = os.path.dirname(os.path.abspath(__file__))
_FRONTEND_DIR = os.path.join(_HERE, "..", "..", "frontend")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'",
        )
        return response


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            resp = await super().get_response(path, scope)
            if path.endswith(".js") or path.endswith(".css"):
                resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return resp
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

    if _settings.seed_demo_data:
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

    app.add_middleware(SecurityHeadersMiddleware)

    if _settings.debug:
        # Dev mode: allow localhost, 127.0.0.1, and common dev-tunnel hosts
        # (VSCode forwarded ports, GitHub Codespaces, Gitpod) on any port.
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=(
                r"^https?://("
                r"localhost"
                r"|127\.0\.0\.1"
                r"|[a-z0-9-]+\.app\.vscode\.dev"
                r"|[a-z0-9-]+\.vscode\.dev"
                r"|[a-z0-9-]+\.cs\.app\.codespaces\.dev"
                r"|[a-z0-9-]+\.app\.codespaces\.dev"
                r"|[a-z0-9-]+\.gitpod\.io"
                r")(:\d+)?$"
            ),
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )
    else:
        # Prod mode: explicit origin allowlist from config
        app.add_middleware(
            CORSMiddleware,
            allow_origins=_settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )

    if HAS_SLOWAPI:
        from slowapi import _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        from slowapi.middleware import SlowAPIMiddleware

        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        app.add_middleware(SlowAPIMiddleware)

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(user_router)
    app.include_router(chunking_router, prefix="/api/v1")
    app.include_router(documents_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")

    if os.path.isdir(_FRONTEND_DIR):
        app.mount("/", SPAStaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")

    return app

