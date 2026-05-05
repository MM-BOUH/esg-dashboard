"""
Settings loaded from environment variables with sensible defaults for local dev.
Call get_settings() wherever config is needed; the result is cached.
"""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    # MongoDB
    mongo_uri: str = Field(default="mongodb://localhost:27017", alias="MONGO_URI")
    mongo_db_name: str = Field(default="esg_dashboard", alias="MONGO_DB_NAME")

    # LLM provider: "anthropic" | "openai"
    llm_provider: str = Field(default="anthropic", alias="LLM_PROVIDER")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(
        default="claude-haiku-4-5-20251001", alias="ANTHROPIC_MODEL"
    )
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    # ChromaDB
    chroma_db_path: str = Field(default="./chroma_db", alias="CHROMA_DB_PATH")
    chroma_collection: str = Field(default="esg_knowledge", alias="CHROMA_COLLECTION")

    # FastAPI
    fastapi_host: str = Field(default="localhost", alias="FASTAPI_HOST")
    fastapi_port: int = Field(default=8000, alias="FASTAPI_PORT")

    model_config = {"populate_by_name": True}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
