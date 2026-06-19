from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import get_settings


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass


class MockLLMProvider(LLMProvider):
    def generate(self, prompt: str) -> str:
        return f"[Mock Response] You asked: {prompt[:100]}..."


class EchoLLMProvider(LLMProvider):
    def generate(self, prompt: str) -> str:
        return f"Echo: {prompt}"


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.debug:
        return EchoLLMProvider()
    return MockLLMProvider()

