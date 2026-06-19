from __future__ import annotations

import os
import sys

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY", "False")

# Python 3.8 compat: prevent posthog (dict[str, X] syntax) from crashing chromadb
import sys as _sys
class _FakePosthog:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None
_sys.modules["posthog"] = _FakePosthog()

try:
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3.dbapi2")
except ImportError:
    pass

import chromadb
from chromadb.api.models.Collection import Collection
import chromadb.config
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from app.core.config import get_settings

_settings = get_settings()

_client: chromadb.PersistentClient | None = None
_embedding_fn: SentenceTransformerEmbeddingFunction | None = None
_collection: Collection | None = None


def get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _settings.chroma_dir.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(_settings.chroma_dir),
            settings=chromadb.config.Settings(anonymized_telemetry=False),
        )
    return _client


def get_embedding_fn():
    global _embedding_fn
    if _embedding_fn is None:
        try:
            _embedding_fn = SentenceTransformerEmbeddingFunction(
                model_name=_settings.embedding_model
            )
        except Exception:
            _embedding_fn = None
    return _embedding_fn


def get_collection() -> Collection:
    global _collection
    if _collection is None:
        client = get_client()
        _collection = client.get_or_create_collection(
            name=_settings.chroma_collection,
            embedding_function=get_embedding_fn(),
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def reset_chroma_client() -> None:
    global _client, _embedding_fn, _collection
    _client = None
    _embedding_fn = None
    _collection = None

