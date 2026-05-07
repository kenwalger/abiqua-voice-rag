from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
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
    RIME_DEFAULT_VOICE: str = "colby"
    LLAMAINDEX_EMBED_MODEL: str = "text-embedding-3-small"
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str
    SCORE_THRESHOLD: float = 0.70
    LOG_LEVEL: str = "INFO"
    IMAGE_BASE_URL: str = ""
    ALLOWED_ORIGINS: list[str] | str = Field(default="http://localhost:5173")

    @model_validator(mode="after")
    def normalize_allowed_origins(self) -> "Settings":
        if isinstance(self.ALLOWED_ORIGINS, str):
            origins = [item.strip() for item in self.ALLOWED_ORIGINS.split(",") if item.strip()]
            self.ALLOWED_ORIGINS = origins or ["http://localhost:5173"]
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

