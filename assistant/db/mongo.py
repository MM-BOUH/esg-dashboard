"""
PyMongo client and typed accessors for the three collections:
  - countries      : one doc per country with all 5 risk scores
  - suppliers      : demo supplier records with risk scores inherited from their country
  - conversations  : chat history keyed by session_id, scoped to user_id
"""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache

from pymongo import DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from assistant.config import get_settings


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    settings = get_settings()
    return MongoClient(settings.mongo_uri)


def get_db() -> Database:
    settings = get_settings()
    return get_client()[settings.mongo_db_name]


def countries_col() -> Collection:
    return get_db()["countries"]


def suppliers_col() -> Collection:
    return get_db()["suppliers"]


def conversations_col() -> Collection:
    return get_db()["conversations"]


# ---------------------------------------------------------------------------
# Conversation helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_conversation(session_id: str) -> list[dict]:
    """Return the ordered list of turns for a session, or [] if none."""
    doc = conversations_col().find_one({"session_id": session_id})
    if doc is None:
        return []
    return doc.get("turns", [])


def get_conversation(session_id: str) -> dict | None:
    """Return the full conversation document, or None."""
    return conversations_col().find_one({"session_id": session_id}, {"_id": 0})


def list_conversations(user_id: str) -> list[dict]:
    """
    Return lightweight conversation summaries for a user,
    sorted by most recently updated first.
    """
    cursor = conversations_col().find(
        {"user_id": user_id},
        {"_id": 0, "session_id": 1, "title": 1, "created_at": 1, "updated_at": 1, "turns": 1},
    ).sort("updated_at", DESCENDING)

    results = []
    for doc in cursor:
        results.append({
            "session_id": doc["session_id"],
            "title": doc.get("title", "New chat"),
            "created_at": doc.get("created_at", ""),
            "updated_at": doc.get("updated_at", ""),
            "turn_count": len(doc.get("turns", [])),
        })
    return results


def append_turn(session_id: str, user_id: str, turn: dict) -> None:
    """
    Push one ConversationTurn dict onto the session's turns array.
    Creates the document if it does not exist.
    On the first turn, sets the title from the user's message.
    """
    now = _now()
    existing = conversations_col().find_one(
        {"session_id": session_id}, {"turns": 1, "title": 1}
    )

    is_first_turn = existing is None or len(existing.get("turns", [])) == 0

    if existing is None:
        # Create a brand new conversation document
        raw_title = turn.get("user_message", "New chat")
        title = raw_title[:60] + ("..." if len(raw_title) > 60 else "")
        conversations_col().insert_one({
            "session_id": session_id,
            "user_id": user_id,
            "title": title,
            "turns": [turn],
            "created_at": now,
            "updated_at": now,
        })
    else:
        update: dict = {
            "$push": {"turns": turn},
            "$set": {"updated_at": now, "user_id": user_id},
        }
        # If the doc existed but had no turns yet, set the title now
        if is_first_turn:
            raw_title = turn.get("user_message", "New chat")
            update["$set"]["title"] = raw_title[:60] + ("..." if len(raw_title) > 60 else "")

        conversations_col().update_one({"session_id": session_id}, update)


def delete_conversation(session_id: str) -> None:
    """Permanently delete a conversation."""
    conversations_col().delete_one({"session_id": session_id})


def rename_conversation(session_id: str, title: str) -> None:
    """Update the display title of a conversation."""
    conversations_col().update_one(
        {"session_id": session_id},
        {"$set": {"title": title, "updated_at": _now()}},
    )


def count_turns_today(user_id: str) -> int:
    """Count LLM turns sent by this user since midnight UTC today."""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    result = list(conversations_col().aggregate([
        {"$match": {"user_id": user_id}},
        {"$unwind": "$turns"},
        {"$match": {"turns.timestamp": {"$gte": today}}},
        {"$count": "total"},
    ]))
    return result[0]["total"] if result else 0
