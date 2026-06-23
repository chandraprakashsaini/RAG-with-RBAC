from __future__ import annotations

import asyncio
from uuid import uuid4

from app.db.chroma import get_collection
from app.models.chunking import ChunkingResponse
from app.models.vector import SearchHit, SearchResponse


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

    return await asyncio.to_thread(_write)


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
        result = collection.get(where={"document_id": document_id})
        if not result["ids"]:
            return 0
        collection.delete(ids=result["ids"])
        return len(result["ids"])

    return await asyncio.to_thread(_delete)


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
    def _get() -> list[str]:
        collection = get_collection()
        result = collection.get(include=["metadatas"])
        names: set[str] = set()
        for meta in result.get("metadatas") or []:
            name = meta.get("document_name")
            if name:
                names.add(str(name))
        return sorted(names)

    return await asyncio.to_thread(_get)

