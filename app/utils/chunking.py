from __future__ import annotations

import math
import re
from enum import Enum


class ChunkStrategy(str, Enum):
    FIXED = "fixed"
    RECURSIVE = "recursive"
    SENTENCE = "sentence"
    TOKEN_APPROX = "token_approx"


def chunk_text(
    text: str,
    strategy: ChunkStrategy = ChunkStrategy.RECURSIVE,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
    separators: list[str] | None = None,
    max_sentences_per_chunk: int = 5,
    estimated_chars_per_token: int = 4,
) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be >= 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    if strategy == ChunkStrategy.FIXED:
        return _fixed_chunks(cleaned, chunk_size, chunk_overlap)
    if strategy == ChunkStrategy.RECURSIVE:
        default_separators = ["\n\n", "\n", ". ", " "]
        return _recursive_chunks(
            cleaned,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators or default_separators,
        )
    if strategy == ChunkStrategy.SENTENCE:
        return _sentence_chunks(cleaned, max_sentences_per_chunk, chunk_size)
    if strategy == ChunkStrategy.TOKEN_APPROX:
        approx_chunk_size = chunk_size * max(estimated_chars_per_token, 1)
        approx_overlap = chunk_overlap * max(estimated_chars_per_token, 1)
        return _fixed_chunks(cleaned, approx_chunk_size, approx_overlap)
    raise ValueError(f"Unsupported strategy: {strategy}")


def _fixed_chunks(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    chunks: list[str] = []
    step = chunk_size - chunk_overlap
    for start in range(0, len(text), step):
        chunk = text[start : start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def _recursive_chunks(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    separators: list[str],
) -> list[str]:
    split = _split_by_separators(text, separators)
    merged = _merge_segments(split, chunk_size)
    return _apply_overlap(merged, chunk_overlap, chunk_size)


def _split_by_separators(text: str, separators: list[str]) -> list[str]:
    segments = [text]
    for sep in separators:
        next_segments: list[str] = []
        for seg in segments:
            if len(seg) <= 1:
                next_segments.append(seg)
                continue
            if sep and sep in seg:
                split_parts = [p.strip() for p in seg.split(sep) if p.strip()]
                if split_parts:
                    next_segments.extend(split_parts)
                else:
                    next_segments.append(seg)
            else:
                next_segments.append(seg)
        segments = next_segments
    return [s for s in segments if s.strip()]


def _merge_segments(segments: list[str], chunk_size: int) -> list[str]:
    merged: list[str] = []
    current = ""
    for seg in segments:
        if len(seg) > chunk_size:
            if current:
                merged.append(current.strip())
                current = ""
            merged.extend(_hard_wrap(seg, chunk_size))
            continue

        candidate = f"{current} {seg}".strip() if current else seg
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            merged.append(current.strip())
            current = seg
    if current:
        merged.append(current.strip())
    return merged


def _hard_wrap(text: str, chunk_size: int) -> list[str]:
    return [text[i : i + chunk_size].strip() for i in range(0, len(text), chunk_size)]


def _apply_overlap(chunks: list[str], chunk_overlap: int, chunk_size: int) -> list[str]:
    if chunk_overlap == 0 or len(chunks) <= 1:
        return chunks

    with_overlap = [chunks[0]]
    for idx in range(1, len(chunks)):
        prev_tail = chunks[idx - 1][-chunk_overlap:]
        candidate = f"{prev_tail} {chunks[idx]}".strip()
        if len(candidate) > chunk_size:
            candidate = candidate[:chunk_size].strip()
        with_overlap.append(candidate)
    return with_overlap


def _sentence_chunks(text: str, max_sentences_per_chunk: int, chunk_size: int) -> list[str]:
    if max_sentences_per_chunk <= 0:
        raise ValueError("max_sentences_per_chunk must be > 0")

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if not sentences:
        return []

    chunks: list[str] = []
    current: list[str] = []
    for sentence in sentences:
        candidate = " ".join(current + [sentence]).strip()
        if len(current) >= max_sentences_per_chunk or len(candidate) > chunk_size:
            if current:
                chunks.append(" ".join(current).strip())
                current = [sentence]
            else:
                chunks.extend(_hard_wrap(sentence, chunk_size))
                current = []
        else:
            current.append(sentence)

    if current:
        chunks.append(" ".join(current).strip())
    return chunks


def estimate_token_count(text: str, estimated_chars_per_token: int = 4) -> int:
    if estimated_chars_per_token <= 0:
        estimated_chars_per_token = 4
    return math.ceil(len(text) / estimated_chars_per_token)

