from __future__ import annotations

import os

# Set test environment BEFORE any app modules are imported by test modules.
# Tests import create_app() which triggers get_settings() at module load; the
# production validator rejects the default JWT_SECRET, so we set a safe test value here.
os.environ.setdefault("JWT_SECRET", "test-secret-key-not-for-production-use-min-16-chars")
os.environ.setdefault("DATABASE_URL", "sqlite:///./app.db")
os.environ.setdefault("CHROMA_DIR", "./data/chroma")
os.environ.setdefault("SEED_DEMO_DATA", "false")
os.environ.setdefault("GEMINI_API_KEY", "")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("LOG_FORMAT", "text")

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: unit tests")
    config.addinivalue_line("markers", "integration: integration tests")


pytest_plugins = ["pytest_asyncio"]