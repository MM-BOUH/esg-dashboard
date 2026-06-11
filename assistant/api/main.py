"""
FastAPI application entry point.

Run from repo root:
    uvicorn assistant.api.main:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from assistant.api.chat import router as chat_router
from assistant.api.conversations import router as conversations_router
from assistant.db.mongo import get_client

app = FastAPI(
    title="ESG Supply Chain RAG Assistant",
    version="1.0.0",
    description="Conversational RAG API for ESG supply chain risk queries.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_methods=["POST", "GET", "DELETE", "PATCH"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(conversations_router)


@app.get("/health")
async def health() -> dict:
    """Liveness probe. Also pings MongoDB so a keep-alive request keeps the
    Mongo connection warm alongside the Render web service. Never raises — a
    Mongo hiccup returns status "degraded" rather than a 500."""
    try:
        get_client().admin.command("ping")
        mongo_ok = True
    except Exception:
        mongo_ok = False
    return {"status": "ok" if mongo_ok else "degraded", "mongo": mongo_ok}
