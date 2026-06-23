from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.utils.chunking import ChunkStrategy


class ChunkingConfig(BaseModel):
    strategy: ChunkStrategy = ChunkStrategy.RECURSIVE
    chunk_size: int = Field(default=800, gt=0)
    chunk_overlap: int = Field(default=120, ge=0)
    separators: Optional[List[str]] = None
    max_sentences_per_chunk: int = Field(default=5, gt=0)
    estimated_chars_per_token: int = Field(default=4, gt=0)


class IngestRequest(BaseModel):
    document_id: UUID
    document_name: str | None = Field(default=None)
    text: str = Field(min_length=1)
    chunking: ChunkingConfig = ChunkingConfig()


class ChunkPreviewRequest(BaseModel):
    text: str = Field(min_length=1)
    chunking: ChunkingConfig = ChunkingConfig()


class ChunkInfo(BaseModel):
    index: int
    content: str
    char_count: int
    estimated_tokens: int


class ChunkingResponse(BaseModel):
    strategy: ChunkStrategy
    chunk_count: int
    chunks: List[ChunkInfo]

