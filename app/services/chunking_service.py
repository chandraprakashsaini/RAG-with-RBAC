import asyncio

from fastapi import HTTPException

from app.models.chunking import ChunkInfo, ChunkingConfig, ChunkingResponse
from app.utils.chunking import chunk_text, estimate_token_count


async def build_chunks_payload(text: str, config: ChunkingConfig) -> ChunkingResponse:
    if config.chunk_overlap >= config.chunk_size:
        raise HTTPException(
            status_code=422,
            detail="chunk_overlap must be smaller than chunk_size",
        )

    try:
        chunks = await asyncio.to_thread(
            chunk_text,
            text=text,
            strategy=config.strategy,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=config.separators,
            max_sentences_per_chunk=config.max_sentences_per_chunk,
            estimated_chars_per_token=config.estimated_chars_per_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    chunk_rows = [
        ChunkInfo(
            index=idx,
            content=chunk,
            char_count=len(chunk),
            estimated_tokens=estimate_token_count(
                chunk,
                estimated_chars_per_token=config.estimated_chars_per_token,
            ),
        )
        for idx, chunk in enumerate(chunks)
    ]

    return ChunkingResponse(
        strategy=config.strategy,
        chunk_count=len(chunk_rows),
        chunks=chunk_rows,
    )

