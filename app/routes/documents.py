from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from starlette.responses import FileResponse

from app.core.auth import CurrentUser, require_role
from app.db.connection import get_db
from app.models.chunking import ChunkingConfig
from app.services.document_service import (
    SUPPORTED_MIME_TYPES,
    check_document_delete_permission,
    create_document_record,
    delete_document,
    detect_mime,
    get_user_document,
    grant_document_permission,
    list_documents,
    list_document_permissions,
    process_uploaded_text,
    read_text_content,
    read_text_content_async,
    revoke_document_permission,
    save_upload_file,
    update_document_permission,
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
    owner_name: str = ""


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]


class DocumentCreateText(BaseModel):
    text: str = Field(min_length=1, max_length=5_000_000)
    document_name: str | None = Field(default=None, max_length=255)
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


class PermissionResponse(BaseModel):
    id: UUID
    document_id: UUID
    role_id: UUID
    role_name: str
    can_read: bool
    can_write: bool
    can_delete: bool
    granted_by: UUID
    granted_by_name: str
    created_at: datetime


class GrantPermissionRequest(BaseModel):
    role_id: UUID
    can_read: bool = True
    can_write: bool = False
    can_delete: bool = False


class UpdatePermissionRequest(BaseModel):
    can_read: Optional[bool] = None
    can_write: Optional[bool] = None
    can_delete: Optional[bool] = None


@router.get("", response_model=DocumentListResponse)
async def list_all_documents(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: CurrentUser = Depends(require_role("admin", "analyst", "manager", "executive", "viewer")),
    db=Depends(get_db),
):
    docs = await list_documents(db, current_user.user_id, current_user.role, limit=limit)
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
                owner_name=doc.user.full_name if doc.user else "",
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

    from app.core.config import get_settings
    settings = get_settings()

    name = document_name or file.filename

    try:
        doc_uuid_str, file_path, file_size = await save_upload_file(
            file.file, file.filename, max_bytes=settings.max_upload_bytes
        )
    except ValueError as e:
        raise HTTPException(status_code=413, detail=str(e))

    if file_size > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed: {settings.max_upload_bytes} bytes.",
        )

    try:
        text = await read_text_content_async(Path(file_path), mime_type)
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
    doc = await get_user_document(db, document_id, current_user.user_id, current_user.role)
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
        owner_name=doc.user.full_name if doc.user else "",
    )


@router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    current_user: CurrentUser = Depends(require_role("admin", "analyst", "manager", "executive", "viewer")),
    db=Depends(get_db),
):
    doc = await get_user_document(db, document_id, current_user.user_id, current_user.role)
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
    limit: int = Query(default=10, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: CurrentUser = Depends(require_role("admin", "analyst", "manager", "executive", "viewer")),
    db=Depends(get_db),
):
    doc = await get_user_document(db, document_id, current_user.user_id, current_user.role)
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
    doc = await check_document_delete_permission(db, document_id, current_user.user_id, current_user.role)
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


# ── Document permission routes ────────────────────────────────────────


@router.get("/{document_id}/permissions", response_model=list[PermissionResponse])
async def get_document_permissions(
    document_id: UUID,
    current_user: CurrentUser = Depends(require_role("admin", "manager")),
    db=Depends(get_db),
):
    doc = await get_user_document(db, document_id, current_user.user_id, current_user.role)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    perms = await list_document_permissions(db, document_id)
    return [
        PermissionResponse(
            id=p.id,
            document_id=p.document_id,
            role_id=p.role_id,
            role_name=p.role.name if p.role else "",
            can_read=p.can_read,
            can_write=p.can_write,
            can_delete=p.can_delete,
            granted_by=p.granted_by,
            granted_by_name=p.grantor.full_name if p.grantor else "",
            created_at=p.created_at,
        )
        for p in perms
    ]


@router.post("/{document_id}/permissions", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_document_permission(
    document_id: UUID,
    request: GrantPermissionRequest,
    current_user: CurrentUser = Depends(require_role("admin", "manager")),
    db=Depends(get_db),
):
    doc = await get_user_document(db, document_id, current_user.user_id, current_user.role)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        perm = await grant_document_permission(
            db=db,
            document_id=document_id,
            role_id=request.role_id,
            can_read=request.can_read,
            can_write=request.can_write,
            can_delete=request.can_delete,
            granted_by=current_user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return PermissionResponse(
        id=perm.id,
        document_id=perm.document_id,
        role_id=perm.role_id,
        role_name=perm.role.name if perm.role else "",
        can_read=perm.can_read,
        can_write=perm.can_write,
        can_delete=perm.can_delete,
        granted_by=perm.granted_by,
        granted_by_name=perm.grantor.full_name if perm.grantor else "",
        created_at=perm.created_at,
    )


@router.put("/{document_id}/permissions/{permission_id}", response_model=PermissionResponse)
async def update_document_permission_route(
    document_id: UUID,
    permission_id: UUID,
    request: UpdatePermissionRequest,
    current_user: CurrentUser = Depends(require_role("admin", "manager")),
    db=Depends(get_db),
):
    doc = await get_user_document(db, document_id, current_user.user_id, current_user.role)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    perm = await update_document_permission(
        db=db,
        permission_id=permission_id,
        can_read=request.can_read,
        can_write=request.can_write,
        can_delete=request.can_delete,
    )
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")

    return PermissionResponse(
        id=perm.id,
        document_id=perm.document_id,
        role_id=perm.role_id,
        role_name=perm.role.name if perm.role else "",
        can_read=perm.can_read,
        can_write=perm.can_write,
        can_delete=perm.can_delete,
        granted_by=perm.granted_by,
        granted_by_name=perm.grantor.full_name if perm.grantor else "",
        created_at=perm.created_at,
    )


@router.delete("/{document_id}/permissions/{permission_id}")
async def revoke_document_permission_route(
    document_id: UUID,
    permission_id: UUID,
    current_user: CurrentUser = Depends(require_role("admin", "manager")),
    db=Depends(get_db),
):
    doc = await get_user_document(db, document_id, current_user.user_id, current_user.role)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    success = await revoke_document_permission(db, permission_id)
    if not success:
        raise HTTPException(status_code=404, detail="Permission not found")

    return {"revoked": True, "permission_id": str(permission_id)}
