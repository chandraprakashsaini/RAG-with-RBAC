from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, gt=0, le=20)
    document_id: Optional[UUID] = None
    document_name: Optional[str] = None


class SearchHit(BaseModel):
    id: str
    document: str
    score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    count: int
    hits: List[SearchHit]

