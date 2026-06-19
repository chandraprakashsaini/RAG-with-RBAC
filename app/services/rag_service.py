from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import UUID

from app.core.config import get_settings

try:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
except ImportError:
    class _Message:
        def __init__(self, content: str):
            self.content = content
    AIMessage = _Message
    HumanMessage = _Message
    SystemMessage = _Message
from app.db.chroma import get_collection
from app.db.models import ChatMessage
from app.llms.provider import get_llm

SYSTEM_PROMPT = """You are a helpful AI assistant for a document analysis platform.
Answer the user's question based on the provided context and conversation history.

Guidelines:
- Use the retrieved document chunks to answer accurately
- If the context doesn't contain enough information, say so honestly
- Cite specific parts of the documents when relevant
- Keep responses clear and concise
- Maintain context from the conversation history"""


def _retrieve_context(query: str, top_k: int = 5) -> list[dict]:
    try:
        collection = get_collection()
    except Exception:
        return []

    try:
        result = collection.query(
            query_texts=[query],
            n_results=top_k,
        )
    except Exception:
        return []

    ids = result.get("ids", [[]])[0]
    documents = result.get("documents", [[]])[0]
    distances = result.get("distances", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]

    chunks = []
    for i in range(len(ids)):
        chunks.append({
            "id": ids[i],
            "content": documents[i],
            "score": distances[i] if i < len(distances) else None,
            "metadata": metadatas[i] if i < len(metadatas) else None,
        })
    return chunks


def _build_context_string(chunks: list[dict]) -> str:
    if not chunks:
        return ""

    parts = ["Retrieved documents:"]
    for i, chunk in enumerate(chunks, 1):
        doc_id = chunk["metadata"].get("document_id", "unknown") if chunk.get("metadata") else "unknown"
        parts.append(f"\n[{i}] (document: {doc_id})\n{chunk['content']}")
    return "".join(parts)


def _build_lc_messages(
    user_message: str,
    chat_messages: list[ChatMessage],
    chunks: list[dict],
) -> list:
    context = _build_context_string(chunks)
    history = _build_history_messages(chat_messages)

    lc_messages = [SystemMessage(content=SYSTEM_PROMPT)]

    if context:
        lc_messages.append(HumanMessage(content=f"Context:\n{context}"))
        lc_messages.append(
            HumanMessage(
                content="Based on the above context, please answer the following question."
            )
        )

    lc_messages.extend(history)
    lc_messages.append(HumanMessage(content=user_message))
    return lc_messages


def _build_history_messages(messages: list[ChatMessage]) -> list:
    lc_messages = []
    for msg in messages[-10:]:
        if msg.sender_type == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        else:
            lc_messages.append(AIMessage(content=msg.content))
    return lc_messages


async def generate_rag_response(
    user_message: str,
    chat_messages: list[ChatMessage],
) -> tuple[str, list[dict]]:
    settings = get_settings()

    chunks = _retrieve_context(user_message, top_k=settings.rag_top_k)

    lc_messages = _build_lc_messages(user_message, chat_messages, chunks)

    if not settings.gemini_api_key:
        chunk_summary = "\n".join(
            f"[{i}] {c['content'][:100]}..." for i, c in enumerate(chunks, 1)
        ) if chunks else "No relevant documents found."
        response_text = (
            f"[RAG Mock] Using {len(chunks)} retrieved chunks.\n\n"
            f"**Context:**\n{chunk_summary}\n\n"
            f"**Your question:** {user_message}\n\n"
            f"Set GEMINI_API_KEY in .env to use Gemini."
        )
        return response_text, chunks

    llm = get_llm()
    response = await llm.ainvoke(lc_messages)
    return response.content, chunks


async def stream_rag_response(
    user_message: str,
    chat_messages: list[ChatMessage],
) -> AsyncGenerator[str, None]:
    settings = get_settings()

    chunks = _retrieve_context(user_message, top_k=settings.rag_top_k)

    lc_messages = _build_lc_messages(user_message, chat_messages, chunks)

    yield f"[CHUNKS]{chunks}[/CHUNKS]"

    if not settings.gemini_api_key:
        chunk_summary = "\n".join(
            f"[{i}] {c['content'][:100]}..." for i, c in enumerate(chunks, 1)
        ) if chunks else "No relevant documents found."
        mock_response = (
            f"[RAG Mock] Using {len(chunks)} retrieved chunks.\n\n"
            f"**Context:**\n{chunk_summary}\n\n"
            f"**Your question:** {user_message}\n\n"
            f"Set GEMINI_API_KEY in .env to use Gemini."
        )
        yield mock_response
        return

    llm = get_llm()
    async for chunk in llm.astream(lc_messages):
        yield chunk.content or ""