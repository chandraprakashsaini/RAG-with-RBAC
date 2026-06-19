from fastapi import FastAPI

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers, setup_logging
from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router
from app.routes.chunking import router as chunking_router
from app.routes.documents import router as documents_router
from app.routes.health import router as health_router

_settings = get_settings()

setup_logging()


def create_app() -> FastAPI:
    app = FastAPI(
        title=_settings.app_name,
        version=_settings.app_version,
        debug=_settings.debug,
    )
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(chunking_router, prefix="/api/v1")
    app.include_router(documents_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")
    return app

