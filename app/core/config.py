from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "RAG RBAC API"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, alias="DEBUG")

    database_url: str = Field(
        default="sqlite:///./app.db", alias="DATABASE_URL"
    )

    chroma_dir: Path = Field(default=Path("./data/chroma"), alias="CHROMA_DIR")
    chroma_collection: str = Field(default="documents", alias="CHROMA_COLLECTION")
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2", alias="EMBEDDING_MODEL"
    )

    jwt_secret: str = Field(
        default="change-me-in-production", alias="JWT_SECRET"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=60, alias="JWT_EXPIRE_MINUTES")

    gemini_api_key: str = Field(
        default="", alias="GEMINI_API_KEY"
    )
    gemini_model: str = Field(
        default="gemini-2.0-flash", alias="GEMINI_MODEL"
    )
    rag_top_k: int = Field(default=5, alias="RAG_TOP_K")
    rag_min_score: float = Field(default=0.0, alias="RAG_MIN_SCORE")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")


@lru_cache
def get_settings() -> Settings:
    return Settings()