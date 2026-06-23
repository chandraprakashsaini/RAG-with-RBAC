from __future__ import annotations

import re
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
from app.core.prompts import get_prompt
from app.db.chroma import get_collection
from app.db.models import ChatMessage
from app.llms.provider import get_decision_llm, get_llm
from app.services.vector_store_service import list_document_names


def _format_history_for_prompt(messages: list) -> str:
    parts = []
    for m in messages:
        if isinstance(m, HumanMessage):
            parts.append(f"User: {m.content}")
        else:
            parts.append(f"Assistant: {m.content}")
    return "\n".join(parts)


def _retrieve_context(
    query: str,
    top_k: int,
    document_names: list[str] | None = None,
    min_score: float = 0.0,
) -> list[dict]:
    try:
        collection = get_collection()
    except Exception:
        return []

    where = None
    if document_names:
        where = {"document_name": {"$in": document_names}}

    try:
        result = collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where,
        )
    except Exception:
        return []

    ids = result.get("ids", [[]])[0]
    documents = result.get("documents", [[]])[0]
    distances = result.get("distances", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]

    chunks = []
    for i in range(len(ids)):
        score = distances[i] if i < len(distances) else None
        if min_score > 0 and score is not None and score > min_score:
            continue
        chunks.append({
            "id": ids[i],
            "content": documents[i],
            "score": score,
            "metadata": metadatas[i] if i < len(metadatas) else None,
        })
    return chunks


def _build_context_string(chunks: list[dict]) -> str:
    if not chunks:
        return ""

    parts = ["Retrieved documents:"]
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata") or {}
        label = meta.get("document_name") or meta.get("document_id", "unknown")
        parts.append(f"\n[{i}] (document: {label})\n{chunk['content']}")
    return "".join(parts)


def _build_lc_messages(
    user_message: str,
    chat_messages: list[ChatMessage],
    chunks: list[dict],
    retrieval_attempted: bool = True,
) -> list:
    prompt_name = "system" if retrieval_attempted else "system_no_context"
    system_prompt = get_prompt(prompt_name)
    context = _build_context_string(chunks)
    history = _build_history_messages(chat_messages)

    lc_messages = [SystemMessage(content=system_prompt)]

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


async def _should_retrieve(
    user_message: str,
    history_messages: list,
    decision_llm,
) -> tuple[bool, list[str] | None]:
    try:
        available_docs = await list_document_names()
        history_text = _format_history_for_prompt(history_messages)
        prompt = get_prompt("decision").format(
            available_docs=", ".join(available_docs) if available_docs else "None",
            history=history_text if history_text else "No prior conversation.",
            user_message=user_message,
        )
        response = await decision_llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content.strip() if hasattr(response, "content") else str(response)

        needs_match = re.search(r"NEED:\s*(YES|NO)", content, re.IGNORECASE)
        needs = bool(needs_match and needs_match.group(1).upper() == "YES")

        docs_match = re.search(r"DOCS:\s*(.+)", content, re.IGNORECASE)
        doc_names: list[str] | None = None
        if docs_match:
            raw = docs_match.group(1).strip()
            if raw.upper() == "ALL":
                doc_names = None
            else:
                parsed = [d.strip() for d in raw.split(",") if d.strip()]
                if parsed:
                    doc_names = parsed

        return needs, doc_names
    except Exception:
        return True, None


async def _rewrite_query(
    user_message: str,
    history_messages: list,
    decision_llm,
) -> str:
    try:
        history_text = _format_history_for_prompt(history_messages)
        prompt = get_prompt("rewrite").format(
            history=history_text if history_text else "No prior conversation.",
            user_message=user_message,
        )
        response = await decision_llm.ainvoke([HumanMessage(content=prompt)])
        rewritten = response.content.strip() if hasattr(response, "content") else str(response)
        return rewritten if rewritten else user_message
    except Exception:
        return user_message


async def generate_rag_response(
    user_message: str,
    chat_messages: list[ChatMessage],
) -> tuple[str, list[dict]]:
    settings = get_settings()
    history = _build_history_messages(chat_messages)

    if not settings.gemini_api_key:
        chunks = _retrieve_context(user_message, top_k=settings.rag_top_k)
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

    decision_llm = get_decision_llm()
    main_llm = get_llm()

    needs_retrieval = True
    doc_filter = None
    if settings.rag_retrieval_decision_enabled:
        needs_retrieval, doc_filter = await _should_retrieve(user_message, history, decision_llm)

    search_query = user_message
    if needs_retrieval and settings.rag_query_rewrite_enabled:
        search_query = await _rewrite_query(user_message, history, decision_llm)

    chunks = []
    if needs_retrieval:
        chunks = _retrieve_context(
            search_query,
            settings.rag_top_k,
            document_names=doc_filter,
            min_score=settings.rag_min_score,
        )

    lc_messages = _build_lc_messages(
        user_message, chat_messages, chunks,
        retrieval_attempted=needs_retrieval,
    )
    response = await main_llm.ainvoke(lc_messages)
    return response.content, chunks


async def stream_rag_response(
    user_message: str,
    chat_messages: list[ChatMessage],
) -> AsyncGenerator[str, None]:
    settings = get_settings()
    history = _build_history_messages(chat_messages)

    if not settings.gemini_api_key:
        chunks = _retrieve_context(user_message, top_k=settings.rag_top_k)
        chunk_summary = "\n".join(
            f"[{i}] {c['content'][:100]}..." for i, c in enumerate(chunks, 1)
        ) if chunks else "No relevant documents found."
        mock_response = (
            f"[RAG Mock] Using {len(chunks)} retrieved chunks.\n\n"
            f"**Context:**\n{chunk_summary}\n\n"
            f"**Your question:** {user_message}\n\n"
            f"Set GEMINI_API_KEY in .env to use Gemini."
        )
        yield f"[CHUNKS]{chunks}[/CHUNKS]"
        yield mock_response
        return

    decision_llm = get_decision_llm()
    main_llm = get_llm()

    needs_retrieval = True
    doc_filter = None
    if settings.rag_retrieval_decision_enabled:
        needs_retrieval, doc_filter = await _should_retrieve(user_message, history, decision_llm)

    search_query = user_message
    if needs_retrieval and settings.rag_query_rewrite_enabled:
        search_query = await _rewrite_query(user_message, history, decision_llm)

    chunks = []
    if needs_retrieval:
        chunks = _retrieve_context(
            search_query,
            settings.rag_top_k,
            document_names=doc_filter,
            min_score=settings.rag_min_score,
        )

    yield f"[CHUNKS]{chunks}[/CHUNKS]"

    lc_messages = _build_lc_messages(
        user_message, chat_messages, chunks,
        retrieval_attempted=needs_retrieval,
    )
    async for chunk in main_llm.astream(lc_messages):
        yield chunk.content or ""
