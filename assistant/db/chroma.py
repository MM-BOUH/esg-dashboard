"""
ChromaDB client and e5-small-v2 embedding function.
The client is created in persistent mode so the index survives restarts.
"""

from __future__ import annotations

from functools import lru_cache

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from assistant.config import get_settings


EMBED_MODEL = "intfloat/e5-small-v2"


@lru_cache(maxsize=1)
def get_embed_fn() -> SentenceTransformerEmbeddingFunction:
    return SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)


@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.ClientAPI:
    settings = get_settings()
    return chromadb.PersistentClient(path=settings.chroma_db_path)


def get_collection() -> chromadb.Collection:
    settings = get_settings()
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=settings.chroma_collection,
        embedding_function=get_embed_fn(),
        metadata={"hnsw:space": "cosine"},
    )
