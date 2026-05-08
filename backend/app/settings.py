from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    MONGODB_URI: str
    MONGODB_DB_NAME: str
    MONGODB_COLLECTION: str
    MONGODB_COLLECTION_FIREARMS: str = "firearms"
    MONGODB_COLLECTION_FIREARMS_CHUNKS: str = "firearms_rag_chunks"
    MONGODB_COLLECTION_HISTORICAL_CHUNKS: str = "historical_events_rag_chunks"
    MONGODB_COLLECTION_MANUFACTURERS_CHUNKS: str = "manufacturers_rag_chunks"
    MONGODB_INDEX_FIREARMS_CHUNKS: str
    MONGODB_INDEX_HISTORICAL_CHUNKS: str
    MONGODB_INDEX_MANUFACTURERS_CHUNKS: str
    MONGODB_EMBEDDING_FIELD: str = "embedding"
    RIME_API_KEY: str
    RIME_BASE_URL: str = "https://users-west.rime.ai"
    # Must match Rime catalog for RIME_DEFAULT_MODEL (e.g. mist eng voices: abbie, …).
    RIME_DEFAULT_VOICE: str = "abbie"
    RIME_DEFAULT_MODEL: str = "mist"
    # When True, JSON error `detail` includes exception type/message (local debugging).
    EXPOSE_INTERNAL_ERRORS: bool = False
    # When True, emit [pipeline] INFO logs for /voices, retrieval, and /query phases (stderr).
    PIPELINE_DEBUG: bool = False
    LLAMAINDEX_EMBED_MODEL: str = "text-embedding-3-small"
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str
    SCORE_THRESHOLD: float = 0.70
    LOG_LEVEL: str = "INFO"
    IMAGE_BASE_URL: str = ""
    # Include both hostnames — browsers send different Origin values for Vite
    # (http://localhost:5173 vs http://127.0.0.1:5173). Missing either causes CORS failures.
    ALLOWED_ORIGINS: list[str] | str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
    )

    @model_validator(mode="after")
    def normalize_allowed_origins(self) -> "Settings":
        if isinstance(self.ALLOWED_ORIGINS, str):
            origins = [item.strip() for item in self.ALLOWED_ORIGINS.split(",") if item.strip()]
            self.ALLOWED_ORIGINS = origins or [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ]
        # De-duplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for o in self.ALLOWED_ORIGINS:
            if o not in seen:
                seen.add(o)
                unique.append(o)
        self.ALLOWED_ORIGINS = unique
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

