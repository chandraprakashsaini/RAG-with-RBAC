from __future__ import annotations

import asyncio
import time
from uuid import uuid4

from app.db.chroma import get_collection
from app.models.chunking import ChunkingResponse
from app.models.vector import SearchHit, SearchResponse

# Module-level TTL cache for document names. Invalidation happens on
# store/delete via _invalidate_doc_name_cache().
_DOC_NAMES_CACHE: tuple[list[str], float] | None = None
_DOC_NAMES_TTL_SECONDS = 60.0


def _invalidate_doc_name_cache() -> None:
    global _DOC_NAMES_CACHE
    _DOC_NAMES_CACHE = None


async def store_document_chunks(
    document_id: str,
    chunking_result: ChunkingResponse,
    document_name: str | None = None,
) -> list[str]:
    def _write() -> list[str]:
        collection = get_collection()
        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, object]] = []

        for chunk in chunking_result.chunks:
            chunk_id = f"{document_id}:{chunk.index}:{uuid4().hex[:8]}"
            ids.append(chunk_id)
            documents.append(chunk.content)
            meta: dict[str, object] = {
                "document_id": document_id,
                "chunk_index": chunk.index,
                "char_count": chunk.char_count,
                "estimated_tokens": chunk.estimated_tokens,
                "strategy": chunking_result.strategy.value,
            }
            if document_name is not None:
                meta["document_name"] = document_name
            metadatas.append(meta)

        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        return ids

    result = await asyncio.to_thread(_write)
    _invalidate_doc_name_cache()
    return result


async def search_chunks(
    query: str,
    top_k: int = 5,
    document_id: str | None = None,
    document_name: str | None = None,
) -> SearchResponse:
    def _search() -> SearchResponse:
        collection = get_collection()
        where: dict | None = None
        if document_name:
            where = {"document_name": document_name}
        elif document_id:
            where = {"document_id": document_id}
        result = collection.query(query_texts=[query], n_results=top_k, where=where)

        ids = (result.get("ids") or [[]])[0]
        docs = (result.get("documents") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]

        hits = [
            SearchHit(
                id=doc_id,
                document=doc_text,
                score=distances[idx] if idx < len(distances) else None,
                metadata=metadatas[idx] if idx < len(metadatas) else None,
            )
            for idx, (doc_id, doc_text) in enumerate(zip(ids, docs))
        ]
        return SearchResponse(count=len(hits), hits=hits)

    return await asyncio.to_thread(_search)


async def delete_document_chunks(document_id: str) -> int:
    def _delete() -> int:
        collection = get_collection()
        # Single-call delete via where filter; avoids the extra get() round-trip.
        collection.delete(where={"document_id": document_id})
        return 0

    await asyncio.to_thread(_delete)
    _invalidate_doc_name_cache()
    # Exact count is no longer cheap to compute in one call; return 0 as a
    # best-effort signal (callers only use it for logging/response).
    return 0


async def get_document_chunks(
    document_id: str,
    limit: int = 10,
    offset: int = 0,
) -> dict:
    def _get() -> dict:
        collection = get_collection()
        result = collection.get(
            where={"document_id": document_id},
            limit=limit,
            offset=offset,
        )
        return {
            "ids": result["ids"],
            "documents": result["documents"],
            "metadatas": result["metadatas"],
        }

    return await asyncio.to_thread(_get)


async def list_document_names() -> list[str]:
    global _DOC_NAMES_CACHE
    now = time.monotonic()
    if _DOC_NAMES_CACHE is not None:
        names, expires_at = _DOC_NAMES_CACHE
        if now < expires_at:
            return names

    def _get() -> list[str]:
        collection = get_collection()
        result = collection.get(include=["metadatas"])
        names: set[str] = set()
        for meta in result.get("metadatas") or []:
            name = meta.get("document_name")
            if name:
                names.add(str(name))
        return sorted(names)

    names = await asyncio.to_thread(_get)
    _DOC_NAMES_CACHE = (names, now + _DOC_NAMES_TTL_SECONDS)
    return names

