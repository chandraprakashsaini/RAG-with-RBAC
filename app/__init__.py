from functools import lru_cache


@lru_cache
def get_app():
    from app.core.application import create_app
    return create_app()

