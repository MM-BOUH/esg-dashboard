"""
ESG Assistant - multi-chat Streamlit UI.

Each conversation is a separate session stored in MongoDB.
user_id is persisted in a local .user_session file so it survives Streamlit
restarts. The URL query param is kept in sync for bookmarking/sharing.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import httpx
import streamlit as st

st.set_page_config(
    page_title="ESG Assistant",
    page_icon="💬",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_BASE = os.getenv("FASTAPI_URL", "http://localhost:8000").rstrip("/chat").rstrip("/")
API_CHAT = f"{_BASE}/chat"
API_CONVERSATIONS = f"{_BASE}/conversations"
TIMEOUT = 120.0

QUERY_TYPE_BADGE = {
    "structured_lookup": "🗄 Data lookup",
    "methodology": "📖 Methodology",
    "combined": "🔀 Combined",
}

# ---------------------------------------------------------------------------
# Persist user_id across Streamlit restarts via a local file
#
# Priority order:
#   1. URL query param  (lets you share/override by pasting a URL)
#   2. .user_session file on disk  (survives server restarts)
#   3. Generate a new UUID and save it to the file
# ---------------------------------------------------------------------------
_SESSION_FILE = Path(__file__).resolve().parents[1] / ".user_session"


def _load_user_id() -> str:
    if "user_id" in st.query_params:
        uid = st.query_params["user_id"]
        _SESSION_FILE.write_text(uid)
        return uid
    if _SESSION_FILE.exists():
        uid = _SESSION_FILE.read_text().strip()
        if uid:
            st.query_params["user_id"] = uid
            return uid
    uid = str(uuid.uuid4())
    _SESSION_FILE.write_text(uid)
    st.query_params["user_id"] = uid
    return uid


USER_ID: str = _load_user_id()

# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------
if "active_session_id" not in st.session_state:
    st.session_state.active_session_id = str(uuid.uuid4())

# Local message cache: { session_id: [{"role", "content", "citations", "query_type"}] }
if "msg_cache" not in st.session_state:
    st.session_state.msg_cache: dict[str, list[dict]] = {}

# Track whether we're in rename mode for a given session
if "renaming" not in st.session_state:
    st.session_state.renaming: str | None = None


# ---------------------------------------------------------------------------
# API helpers (synchronous — Streamlit is not async)
# ---------------------------------------------------------------------------
def api_list_conversations() -> list[dict]:
    try:
        r = httpx.get(API_CONVERSATIONS, params={"user_id": USER_ID}, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def api_get_turns(session_id: str) -> list[dict]:
    try:
        r = httpx.get(f"{API_CONVERSATIONS}/{session_id}", timeout=10)
        r.raise_for_status()
        return r.json().get("turns", [])
    except Exception:
        return []


def api_delete(session_id: str) -> None:
    try:
        httpx.delete(f"{API_CONVERSATIONS}/{session_id}", timeout=10)
    except Exception:
        pass


def api_rename(session_id: str, title: str) -> None:
    try:
        httpx.patch(
            f"{API_CONVERSATIONS}/{session_id}/title",
            json={"title": title},
            timeout=10,
        )
    except Exception:
        pass


def api_chat(session_id: str, query: str) -> dict:
    r = httpx.post(
        API_CHAT,
        json={"session_id": session_id, "user_id": USER_ID, "query": query},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Message cache helpers
# ---------------------------------------------------------------------------
def turns_to_messages(turns: list[dict]) -> list[dict]:
    """Convert MongoDB turn dicts to local display message dicts."""
    msgs = []
    for t in turns:
        msgs.append({"role": "user", "content": t.get("user_message", ""), "citations": [], "query_type": ""})
        msgs.append({
            "role": "assistant",
            "content": t.get("assistant_message", ""),
            "citations": t.get("citations", []),
            "query_type": t.get("query_type", ""),
        })
    return msgs


def get_messages(session_id: str) -> list[dict]:
    """Return cached messages, loading from API if not yet cached."""
    if session_id not in st.session_state.msg_cache:
        turns = api_get_turns(session_id)
        st.session_state.msg_cache[session_id] = turns_to_messages(turns)
    return st.session_state.msg_cache[session_id]


# ---------------------------------------------------------------------------
# Sidebar: conversation list
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("💬 ESG Assistant")

    if st.button("＋  New chat", use_container_width=True, type="primary"):
        st.session_state.active_session_id = str(uuid.uuid4())
        st.session_state.renaming = None
        st.rerun()

    st.divider()

    conversations = api_list_conversations()
    active_id = st.session_state.active_session_id

    if not conversations:
        st.caption("No saved chats yet. Ask a question to start.")
    else:
        st.caption(f"{len(conversations)} chat(s)")

    for conv in conversations:
        sid = conv["session_id"]
        title = conv["title"] or "New chat"
        display = title[:32] + "…" if len(title) > 32 else title
        is_active = sid == active_id

        # Rename mode: show an input for this specific conversation
        if st.session_state.renaming == sid:
            new_title = st.text_input(
                "Rename", value=title, key=f"rename_input_{sid}", label_visibility="collapsed"
            )
            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.button("Save", key=f"save_{sid}", use_container_width=True):
                    api_rename(sid, new_title)
                    # update local cache for conversations
                    st.session_state.renaming = None
                    st.rerun()
            with col_cancel:
                if st.button("Cancel", key=f"cancel_{sid}", use_container_width=True):
                    st.session_state.renaming = None
                    st.rerun()
            continue

        # Normal row: title button + action buttons
        col_title, col_edit, col_del = st.columns([6, 1, 1])

        with col_title:
            if st.button(
                display,
                key=f"conv_{sid}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.active_session_id = sid
                st.session_state.renaming = None
                st.rerun()

        with col_edit:
            if st.button("✏️", key=f"edit_{sid}", help="Rename"):
                st.session_state.renaming = sid
                st.rerun()

        with col_del:
            if st.button("🗑️", key=f"del_{sid}", help="Delete"):
                api_delete(sid)
                st.session_state.msg_cache.pop(sid, None)
                if is_active:
                    st.session_state.active_session_id = str(uuid.uuid4())
                st.rerun()

    st.divider()
    if "daily_used" in st.session_state and "daily_limit" in st.session_state:
        used = st.session_state.daily_used
        limit = st.session_state.daily_limit
        pct = used / limit
        st.caption(f"Messages today: {used}/{limit}")
        st.progress(pct)
    st.caption(f"User ID: `{USER_ID[:8]}…`")


# ---------------------------------------------------------------------------
# Main chat area
# ---------------------------------------------------------------------------
active_id = st.session_state.active_session_id
messages = get_messages(active_id)

# Show a placeholder header when the chat is empty
if not messages:
    st.markdown("## What do you want to know about your supply chain?")
    with st.expander("Example questions", expanded=True):
        st.markdown(
            """
            - Which of my suppliers have the highest forced-labor risk?
            - Compare my China vs Vietnam suppliers on water stress.
            - What does the CPI score measure and how is it calculated?
            - Which material has the highest CO2 risk?
            - What is the overall ESG risk for Bangladesh?
            """
        )

# Render existing messages
for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("citations"):
            with st.expander(f"Sources ({len(msg['citations'])})", expanded=False):
                for cit in msg["citations"]:
                    source = cit.get("source", "")
                    indicator = cit.get("indicator", "")
                    url = cit.get("url", "")
                    label = f"**{indicator}** — {source}" if indicator else f"**{source}**"
                    st.markdown(f"- {label} ([link]({url}))" if url else f"- {label}")
            badge = QUERY_TYPE_BADGE.get(msg.get("query_type", ""), "")
            if badge:
                st.caption(badge)

# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------
query = st.chat_input("Ask about your supply chain ESG risks...")

if query:
    # Render user bubble immediately
    with st.chat_message("user"):
        st.markdown(query)
    st.session_state.msg_cache.setdefault(active_id, []).append(
        {"role": "user", "content": query, "citations": [], "query_type": ""}
    )

    # Call API and render assistant bubble
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                data = api_chat(active_id, query)
                answer = data["answer"]
                citations = data.get("citations", [])
                query_type = data.get("query_type", "combined")
                st.session_state.daily_used = data.get("messages_used", 0)
                st.session_state.daily_limit = data.get("messages_limit", 10)

                st.markdown(answer)

                if citations:
                    with st.expander(f"Sources ({len(citations)})", expanded=False):
                        for cit in citations:
                            source = cit.get("source", "")
                            indicator = cit.get("indicator", "")
                            url = cit.get("url", "")
                            label = f"**{indicator}** — {source}" if indicator else f"**{source}**"
                            st.markdown(f"- {label} ([link]({url}))" if url else f"- {label}")

                badge = QUERY_TYPE_BADGE.get(query_type, "")
                if badge:
                    st.caption(badge)

                st.session_state.msg_cache[active_id].append({
                    "role": "assistant",
                    "content": answer,
                    "citations": citations,
                    "query_type": query_type,
                })

                # Rerun so the sidebar title updates after the first message
                if len(st.session_state.msg_cache[active_id]) == 2:
                    st.rerun()

            except httpx.ConnectError:
                err = (
                    "Cannot reach the assistant API. "
                    "Make sure the FastAPI server is running:\n\n"
                    "```\nuvicorn assistant.api.main:app --reload --port 8000\n```"
                )
                st.error(err)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    st.warning("You've reached the daily limit of 10 messages. Come back tomorrow!")
                else:
                    st.error(f"API error {e.response.status_code}: {e.response.text}")

            except Exception as e:
                st.error(f"Unexpected error: {e}")
