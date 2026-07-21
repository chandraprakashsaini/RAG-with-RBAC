from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection import AsyncSessionLocal
from app.db.models import Chat, ChatMessage
from app.services.rag_service import generate_rag_response, stream_rag_response


async def create_chat(user_id: UUID, title: str) -> Chat:
    async with AsyncSessionLocal() as db:
        chat = Chat(user_id=user_id, title=title)
        db.add(chat)
        await db.commit()
        await db.refresh(chat)
        return chat


async def list_chats(user_id: UUID, limit: int = 100) -> list[Chat]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Chat)
            .where(Chat.user_id == user_id)
            .order_by(Chat.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


async def get_chat(chat_id: UUID, user_id: UUID) -> Chat | None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id)
        )
        return result.scalar_one_or_none()


async def get_messages(chat_id: UUID, limit: int | None = 50) -> list[ChatMessage]:
    async with AsyncSessionLocal() as db:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.chat_id == chat_id)
            .order_by(ChatMessage.created_at)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())


async def add_message(chat_id: UUID, sender_type: str, content: str) -> ChatMessage:
    async with AsyncSessionLocal() as db:
        message = ChatMessage(chat_id=chat_id, sender_type=sender_type, content=content)
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message


async def delete_chat(chat_id: UUID, user_id: UUID) -> bool:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id)
        )
        chat = result.scalar_one_or_none()
        if not chat:
            return False
        await db.delete(chat)
        await db.commit()
        return True


async def send_message(chat_id: UUID, user_id: UUID, content: str) -> tuple[ChatMessage, list[dict]]:
    chat = await get_chat(chat_id, user_id)
    if not chat:
        raise ValueError("Chat not found")

    user_message = await add_message(chat_id, "user", content)

    messages = await get_messages(chat_id, limit=50)

    assistant_response, retrieved_chunks = await generate_rag_response(
        user_message=content,
        chat_messages=messages,
    )

    assistant_message = await add_message(chat_id, "assistant", assistant_response)

    return assistant_message, retrieved_chunks


async def send_message_stream(
    chat_id: UUID, user_id: UUID, content: str
) -> AsyncGenerator[str, None]:
    chat = await get_chat(chat_id, user_id)
    if not chat:
        raise ValueError("Chat not found")

    await add_message(chat_id, "user", content)
    messages = await get_messages(chat_id, limit=50)

    full_response: list[str] = []
    try:
        async for token in stream_rag_response(
            user_message=content,
            chat_messages=messages,
        ):
            if token.startswith("[CHUNKS]") and token.endswith("[/CHUNKS]"):
                yield token
            else:
                full_response.append(token)
                yield token
    finally:
        # Persist whatever was accumulated, even if the client disconnected
        # mid-stream (generator cancellation). Avoids losing the partial
        # assistant response and lets the user see it later.
        complete_content = "".join(full_response)
        if complete_content:
            await add_message(chat_id, "assistant", complete_content)