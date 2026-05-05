"""
POST /chat endpoint.

Request:  ChatRequest  { session_id, query }
Response: ChatResponse { session_id, answer, citations, query_type }

Orchestration (plain async Python, LangChain used only for LLM + prompt):
  1. Load conversation history from MongoDB.
  2. Classify query type with the router.
  3. Retrieve structured data from MongoDB and/or semantic chunks from ChromaDB.
  4. Assemble context and citations.
  5. Build prompt and call LLM.
  6. Persist the new turn to MongoDB.
  7. Return the response.
"""

from __future__ import annotations

import asyncio
from functools import partial

from fastapi import APIRouter, HTTPException

from assistant.core.context import assemble_context
from assistant.core.llm import format_history, get_llm
from assistant.core.prompt import PROMPT_MAP
from assistant.core.retrieval import retrieve_semantic, retrieve_structured
from assistant.core.router import QueryType, classify
from assistant.db.mongo import append_turn, count_turns_today, load_conversation
from assistant.models.schemas import ChatRequest, ChatResponse, ConversationTurn

DAILY_LIMIT = 10

router = APIRouter()


def _run_retrieval(query: str, query_type: QueryType) -> tuple[list[dict], list[dict]]:
    """Return (structured_results, semantic_results) based on query type."""
    structured: list[dict] = []
    semantic: list[dict] = []

    if query_type in ("structured_lookup", "combined"):
        structured = retrieve_structured(query)

    if query_type in ("methodology", "combined"):
        semantic = retrieve_semantic(query, n_results=5)

    return structured, semantic


def _invoke_llm(query: str, context: str, history: str, query_type: QueryType) -> str:
    """Build the prompt chain and invoke the LLM synchronously."""
    prompt = PROMPT_MAP[query_type]
    llm = get_llm()
    chain = prompt | llm
    result = chain.invoke({"query": query, "context": context, "history": history})
    return result.content


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    loop = asyncio.get_event_loop()

    # 1. Enforce daily rate limit
    used = await loop.run_in_executor(None, partial(count_turns_today, request.user_id))
    if used >= DAILY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Daily limit of {DAILY_LIMIT} messages reached. Come back tomorrow.",
        )

    # 2. Load history
    turns = load_conversation(request.session_id)
    history = format_history(turns)

    # 2. Classify
    query_type = classify(request.query)

    # 3. Retrieve (run in thread pool so we don't block the event loop)
    structured, semantic = await loop.run_in_executor(
        None, partial(_run_retrieval, request.query, query_type)
    )

    # 4. Assemble context
    context, citations = assemble_context(structured, semantic)

    if not context.strip():
        context = "No relevant data found in the knowledge base for this query."

    # 5. Call LLM
    answer = await loop.run_in_executor(
        None,
        partial(_invoke_llm, request.query, context, history, query_type),
    )

    # 6. Persist turn
    turn = ConversationTurn(
        user_message=request.query,
        assistant_message=answer,
        citations=[c.model_dump() for c in citations],
        query_type=query_type,
    )
    await loop.run_in_executor(
        None, partial(append_turn, request.session_id, request.user_id, turn.model_dump())
    )

    # 7. Return
    return ChatResponse(
        session_id=request.session_id,
        answer=answer,
        citations=citations,
        query_type=query_type,
        messages_used=used + 1,
        messages_limit=DAILY_LIMIT,
    )
