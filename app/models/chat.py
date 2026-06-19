from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class UserRoleResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    created_at: datetime


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ChatResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ChatMessageResponse(BaseModel):
    id: UUID
    chat_id: UUID
    sender_type: str = Field(min_length=1, max_length=20)
    content: str
    created_at: datetime

