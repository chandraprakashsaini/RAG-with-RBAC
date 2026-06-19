from __future__ import annotations

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: unit tests")
    config.addinivalue_line("markers", "integration: integration tests")


pytest_plugins = ["pytest_asyncio"]