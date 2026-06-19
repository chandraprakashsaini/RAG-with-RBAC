from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user, require_role
from app.models.chunking import ChunkPreviewRequest, ChunkingResponse, IngestRequest
from app.models.vector import SearchRequest, SearchResponse
from app.services.chunking_service import build_chunks_payload
from app.services.vector_store_service import search_chunks, store_document_chunks

router = APIRouter(tags=["chunking"])


@router.post("/chunk-preview", response_model=ChunkingResponse)
async def chunk_preview(
    request: ChunkPreviewRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ChunkingResponse:
    return await build_chunks_payload(request.text, request.chunking)


@router.post("/ingest")
async def ingest_document(
    request: IngestRequest,
    current_user: CurrentUser = Depends(require_role("admin", "analyst", "manager")),
) -> Dict[str, Any]:
    chunking_result = await build_chunks_payload(request.text, request.chunking)
    stored_chunk_ids = await store_document_chunks(
        document_id=str(request.document_id),
        chunking_result=chunking_result,
    )

    return {
        "document_id": str(request.document_id),
        "chunking_strategy": chunking_result.strategy,
        "chunk_count": chunking_result.chunk_count,
        "stored_chunk_ids": stored_chunk_ids,
        "chunks": [chunk.model_dump() for chunk in chunking_result.chunks[:3]],
    }


@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    current_user: CurrentUser = Depends(require_role("admin", "analyst", "manager", "executive", "viewer")),
) -> SearchResponse:
    return await search_chunks(
        query=request.query,
        top_k=request.top_k,
        document_id=str(request.document_id) if request.document_id else None,
    )

