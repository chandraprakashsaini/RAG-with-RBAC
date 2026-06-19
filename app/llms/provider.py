from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings

try:
    from langchain_google_genai import ChatGoogleGenerativeAI

    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False


class FallbackLLM:
    def __init__(self, model: str, google_api_key: str, **kwargs):
        self.model = model
        self.google_api_key = google_api_key

    async def ainvoke(self, messages):
        return AIMessageChunk(content="[LLM not available] Install langchain-google-genai with Python 3.9+ to use Gemini.")

    def astream(self, messages):
        return self._async_gen()

    async def _async_gen(self):
        yield AIMessageChunk(content="[LLM not available] Install langchain-google-genai with Python 3.9+ to use Gemini.")


class AIMessageChunk:
    def __init__(self, content: str):
        self.content = content


@lru_cache
def get_llm():
    settings = get_settings()
    if HAS_LANGCHAIN:
        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0.7,
            top_p=0.95,
            convert_system_message_to_human=True,
        )
    return FallbackLLM(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
    )
