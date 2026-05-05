"""Pydantic models for the chat API request/response cycle and conversation storage."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str
    user_id: str
    query: str


class Citation(BaseModel):
    source: str
    indicator: str | None = None
    url: str | None = None
    chunk_index: int | None = None


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    citations: list[Citation] = Field(default_factory=list)
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    citations: list[Citation]
    query_type: Literal["structured_lookup", "methodology", "combined"]
    messages_used: int
    messages_limit: int


class ConversationSummary(BaseModel):
    """Lightweight representation used for the sidebar list."""
    session_id: str
    title: str
    created_at: str
    updated_at: str
    turn_count: int


class ConversationDetail(BaseModel):
    """Full conversation returned when opening a chat."""
    session_id: str
    title: str
    turns: list[dict]


class ConversationTurn(BaseModel):
    """One round-trip (user message + assistant reply) stored in MongoDB."""
    user_message: str
    assistant_message: str
    citations: list[Citation]
    query_type: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
