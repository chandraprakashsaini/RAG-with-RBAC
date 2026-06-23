from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from starlette.responses import FileResponse

from app.core.auth import CurrentUser, require_role
from app.db.connection import get_db
from app.models.chunking import ChunkingConfig
from app.services.document_service import (
    SUPPORTED_MIME_TYPES,
    create_document_record,
    delete_document,
    detect_mime,
    get_user_document,
    list_documents,
    process_uploaded_text,
    read_text_content,
    save_upload_file,
)
from app.services.vector_store_service import (
    get_document_chunks as svc_get_document_chunks,
)

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    id: UUID
    original_filename: str
    file_size: int
    mime_type: str
    document_id: UUID
    chunk_count: int
    created_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]


class DocumentCreateText(BaseModel):
    text: str
    document_name: str | None = None
    chunking: ChunkingConfig = ChunkingConfig()


class DocumentCreateResponse(BaseModel):
    id: UUID
    document_id: UUID
    chunk_count: int
    text_preview: str


class DocumentChunksResponse(BaseModel):
    document_id: str
    chunks: list[dict]
    total: int


@router.get("", response_model=DocumentListResponse)
async def list_all_documents(
    current_user: CurrentUser = Depends(require_role("admin", "analyst", "manager", "executive", "viewer")),
    db=Depends(get_db),
):
    docs = await list_documents(db, current_user.user_id)
    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=doc.id,
                original_filename=doc.original_filename,
                file_size=doc.file_size,
                mime_type=doc.mime_type,
                document_id=doc.document_id,
                chunk_count=doc.chunk_count,
                created_at=doc.created_at,
            )
            for doc in docs
        ]
    )


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    document_name: str | None = Form(default=None),
    current_user: CurrentUser = Depends(require_role("admin", "analyst", "manager")),
    db=Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    mime_type = detect_mime(file.filename)
    if mime_type is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported: {', '.join(SUPPORTED_MIME_TYPES.keys())}",
        )

    name = document_name or file.filename

    doc_uuid_str, file_path, file_size = await save_upload_file(file.file, file.filename)

    try:
        text = read_text_content(Path(file_path), mime_type)
    except Exception as e:
        Path(file_path).unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Could not read file content: {e}")

    document_id, chunk_count = await process_uploaded_text(text, document_name=name)

    doc = await create_document_record(
        db=db,
        user_id=current_user.user_id,
        original_filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type,
        document_id=UUID(document_id),
        chunk_count=chunk_count,
    )

    return DocumentResponse(
        id=doc.id,
        original_filename=doc.original_filename,
        file_size=doc.file_size,
        mime_type=doc.mime_type,
        document_id=doc.document_id,
        chunk_count=doc.chunk_count,
        created_at=doc.created_at,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    current_user: CurrentUser = Depends(require_role("admin", "analyst", "manager", "executive", "viewer")),
    db=Depends(get_db),
):
    doc = await get_user_document(db, document_id, current_user.user_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse(
        id=doc.id,
        original_filename=doc.original_filename,
        file_size=doc.file_size,
        mime_type=doc.mime_type,
        document_id=doc.document_id,
        chunk_count=doc.chunk_count,
        created_at=doc.created_at,
    )


@router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    current_user: CurrentUser = Depends(require_role("admin", "analyst", "manager", "executive", "viewer")),
    db=Depends(get_db),
):
    doc = await get_user_document(db, document_id, current_user.user_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=str(file_path),
        filename=doc.original_filename,
        media_type=doc.mime_type,
    )


@router.get("/{document_id}/chunks", response_model=DocumentChunksResponse)
async def get_document_chunks(
    document_id: UUID,
    limit: int = 10,
    offset: int = 0,
    current_user: CurrentUser = Depends(require_role("admin", "analyst", "manager", "executive", "viewer")),
    db=Depends(get_db),
):
    doc = await get_user_document(db, document_id, current_user.user_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    result = await svc_get_document_chunks(
        document_id=str(doc.document_id),
        limit=limit,
        offset=offset,
    )

    return DocumentChunksResponse(
        document_id=str(doc.document_id),
        chunks=[
            {
                "id": chunk_id,
                "content": doc_text,
                "metadata": meta,
            }
            for chunk_id, doc_text, meta in zip(
                result["ids"],
                result["documents"],
                result["metadatas"],
            )
        ],
        total=len(result["ids"]),
    )


@router.delete("/{document_id}")
async def delete_document_endpoint(
    document_id: UUID,
    current_user: CurrentUser = Depends(require_role("admin", "manager")),
    db=Depends(get_db),
):
    doc = await get_user_document(db, document_id, current_user.user_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    await delete_document(db, doc)
    return {"deleted": True, "document_id": str(document_id)}


@router.post("", response_model=DocumentCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_document_text(
    request: DocumentCreateText,
    current_user: CurrentUser = Depends(require_role("admin", "analyst", "manager")),
    db=Depends(get_db),
):
    document_id, chunk_count = await process_uploaded_text(
        request.text,
        document_name=request.document_name,
        chunking=request.chunking,
    )

    doc = await create_document_record(
        db=db,
        user_id=current_user.user_id,
        original_filename=request.document_name or "text_input.txt",
        file_path="",
        file_size=len(request.text.encode("utf-8")),
        mime_type="text/plain",
        document_id=UUID(document_id),
        chunk_count=chunk_count,
    )

    return DocumentCreateResponse(
        id=doc.id,
        document_id=doc.document_id,
        chunk_count=doc.chunk_count,
        text_preview=request.text[:200] + ("..." if len(request.text) > 200 else ""),
    )
