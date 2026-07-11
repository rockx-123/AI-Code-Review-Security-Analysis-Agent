"""
Centralized, env-driven configuration.

Nothing in this project should hardcode a path, model name, or limit inline — it should read
from here, so later milestones (and deployment) only ever touch one file.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Submission module ---
    max_upload_size_bytes: int = 1_048_576  # 1 MB
    allowed_extensions: str = ".py,.java"

    # --- RAG / vector store ---
    vector_store_dir: str = "./data/vector_store"
    vector_store_collection: str = "secure_coding_kb"
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size_tokens: int = 300
    chunk_overlap_tokens: int = 50

    # --- Reserved for later milestones ---
    llm_provider: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_extension_list(self) -> list[str]:
        return [ext.strip() for ext in self.allowed_extensions.split(",") if ext.strip()]

    @property
    def vector_store_path(self) -> Path:
        path = Path(self.vector_store_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
