from __future__ import annotations

import json
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.auth import CurrentUser, get_current_user
from app.services.chat_service import (
    create_chat,
    list_chats,
    get_chat as svc_get_chat,
    get_messages,
    send_message as svc_send_message,
    send_message_stream,
    delete_chat as svc_delete_chat,
)

router = APIRouter(prefix="/chats", tags=["chat"])


class ChatCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ChatResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    created_at: str
    updated_at: str


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1)


class ChatMessageResponse(BaseModel):
    id: UUID
    chat_id: UUID
    sender_type: str
    content: str
    created_at: str


class ChatMessageWithContext(BaseModel):
    id: UUID
    chat_id: UUID
    sender_type: str
    content: str
    created_at: str
    retrieved_chunks: list[dict] | None = None


class ChatWithMessagesResponse(BaseModel):
    chat: ChatResponse
    messages: list[ChatMessageResponse]


@router.post("", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_endpoint(
    request: ChatCreate,
    current_user: CurrentUser = Depends(get_current_user),
):
    chat = await create_chat(current_user.user_id, request.title)

    return ChatResponse(
        id=chat.id,
        user_id=chat.user_id,
        title=chat.title,
        created_at=chat.created_at.isoformat(),
        updated_at=chat.updated_at.isoformat(),
    )


@router.get("", response_model=List[ChatResponse])
async def list_chats_endpoint(
    current_user: CurrentUser = Depends(get_current_user),
):
    chats = await list_chats(current_user.user_id)
    return [
        ChatResponse(
            id=chat.id,
            user_id=chat.user_id,
            title=chat.title,
            created_at=chat.created_at.isoformat(),
            updated_at=chat.updated_at.isoformat(),
        )
        for chat in chats
    ]


@router.get("/{chat_id}", response_model=ChatWithMessagesResponse)
async def get_chat_endpoint(
    chat_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
):
    chat = await svc_get_chat(chat_id, current_user.user_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    messages = await get_messages(chat_id)

    return ChatWithMessagesResponse(
        chat=ChatResponse(
            id=chat.id,
            user_id=chat.user_id,
            title=chat.title,
            created_at=chat.created_at.isoformat(),
            updated_at=chat.updated_at.isoformat(),
        ),
        messages=[
            ChatMessageResponse(
                id=msg.id,
                chat_id=msg.chat_id,
                sender_type=msg.sender_type,
                content=msg.content,
                created_at=msg.created_at.isoformat(),
            )
            for msg in messages
        ],
    )


@router.post("/{chat_id}/messages", response_model=ChatMessageWithContext, status_code=status.HTTP_201_CREATED)
async def send_message_endpoint(
    chat_id: UUID,
    request: ChatMessageCreate,
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        assistant_message, retrieved_chunks = await svc_send_message(chat_id, current_user.user_id, request.content)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return ChatMessageWithContext(
        id=assistant_message.id,
        chat_id=assistant_message.chat_id,
        sender_type=assistant_message.sender_type,
        content=assistant_message.content,
        created_at=assistant_message.created_at.isoformat(),
        retrieved_chunks=retrieved_chunks,
    )


@router.post("/{chat_id}/messages/stream")
async def stream_message_endpoint(
    chat_id: UUID,
    request: ChatMessageCreate,
    current_user: CurrentUser = Depends(get_current_user),
):
    async def event_generator():
        try:
            async for token in send_message_stream(
                chat_id, current_user.user_id, request.content
            ):
                if token.startswith("[CHUNKS]") and token.endswith("[/CHUNKS]"):
                    chunks_data = token[8:-9]
                    yield f"event: chunks\ndata: {chunks_data}\n\n"
                else:
                    safe = json.dumps({"token": token})
                    yield f"data: {safe}\n\n"
            yield "event: done\ndata: {}\n\n"
        except ValueError as e:
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_endpoint(
    chat_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
):
    deleted = await svc_delete_chat(chat_id, current_user.user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )