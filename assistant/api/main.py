"""
FastAPI application entry point.

Run from repo root:
    uvicorn assistant.api.main:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from assistant.api.chat import router as chat_router
from assistant.api.conversations import router as conversations_router

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
    return {"status": "ok"}
