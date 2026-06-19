from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import CurrentUser, get_current_user, require_role
from app.services.vector_store_service import (
    store_document_chunks,
    delete_document_chunks,
    get_document_chunks as svc_get_document_chunks,
)
from app.services.chunking_service import build_chunks_payload
from app.models.chunking import ChunkingConfig

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentCreate(BaseModel):
    text: str
    chunking: ChunkingConfig = ChunkingConfig()


class DocumentResponse(BaseModel):
    id: UUID
    text_preview: str
    chunk_count: int
    chunking_strategy: str
    created_at: str


class DocumentDeleteResponse(BaseModel):
    document_id: UUID
    deleted: bool


class DocumentChunksResponse(BaseModel):
    document_id: str
    chunks: list[dict]
    total: int


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    request: DocumentCreate,
    current_user: CurrentUser = Depends(require_role("admin", "analyst", "manager")),
):
    chunking_result = await build_chunks_payload(request.text, request.chunking)
    
    document_id = UUID(int=0)
    stored_chunk_ids = await store_document_chunks(
        document_id=str(document_id),
        chunking_result=chunking_result,
    )

    return DocumentResponse(
        id=document_id,
        text_preview=request.text[:200] + ("..." if len(request.text) > 200 else ""),
        chunk_count=chunking_result.chunk_count,
        chunking_strategy=chunking_result.strategy.value,
        created_at="",
    )


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    document_id: UUID,
    current_user: CurrentUser = Depends(require_role("admin", "manager")),
):
    deleted_count = await delete_document_chunks(str(document_id))
    if deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    return DocumentDeleteResponse(document_id=document_id, deleted=True)


@router.get("/{document_id}/chunks", response_model=DocumentChunksResponse)
async def get_document_chunks(
    document_id: UUID,
    limit: int = 10,
    offset: int = 0,
    current_user: CurrentUser = Depends(require_role("admin", "analyst", "manager", "executive", "viewer")),
):
    result = await svc_get_document_chunks(
        document_id=str(document_id),
        limit=limit,
        offset=offset,
    )
    
    return DocumentChunksResponse(
        document_id=str(document_id),
        chunks=[
            {
                "id": chunk_id,
                "content": doc,
                "metadata": meta,
            }
            for chunk_id, doc, meta in zip(
                result["ids"],
                result["documents"],
                result["metadatas"],
            )
        ],
        total=len(result["ids"]),
    )