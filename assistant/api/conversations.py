"""
Conversation management endpoints.

GET  /conversations?user_id=...          list all chats for a user
GET  /conversations/{session_id}         full chat (turns) for display
DELETE /conversations/{session_id}       delete a chat
PATCH  /conversations/{session_id}/title rename a chat
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from assistant.db.mongo import (
    delete_conversation,
    get_conversation,
    list_conversations,
    rename_conversation,
)
from assistant.models.schemas import ConversationDetail, ConversationSummary

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationSummary])
async def get_conversations(user_id: str = Query(...)) -> list[ConversationSummary]:
    """Return all conversations for a user, most recent first."""
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required.")
    docs = list_conversations(user_id)
    return [ConversationSummary(**d) for d in docs]


@router.get("/{session_id}", response_model=ConversationDetail)
async def get_conversation_detail(session_id: str) -> ConversationDetail:
    """Return the full conversation including all turns."""
    doc = get_conversation(session_id)
    if doc is None:
        return ConversationDetail(session_id=session_id, title="New chat", turns=[])
    return ConversationDetail(
        session_id=doc["session_id"],
        title=doc.get("title", "New chat"),
        turns=doc.get("turns", []),
    )


@router.delete("/{session_id}", status_code=204)
async def remove_conversation(session_id: str) -> None:
    """Permanently delete a conversation."""
    delete_conversation(session_id)


class RenameRequest(BaseModel):
    title: str


@router.patch("/{session_id}/title", status_code=204)
async def update_title(session_id: str, body: RenameRequest) -> None:
    """Rename a conversation."""
    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title must not be empty.")
    rename_conversation(session_id, title)
