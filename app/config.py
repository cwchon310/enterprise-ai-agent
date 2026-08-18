"""Application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load configuration from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
    )

    # Security
    api_key: str = Field(default="dev-secret-key", alias="AGENT_API_KEY")
    token_header: str = "Authorization"
    token_prefix: str = "Bearer "

    # LLM provider
    llm_provider: Literal["deepseek", "openai", "ollama", "rule"] = "rule"

    # DeepSeek
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Ollama (local)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"

    # Storage
    db_path: str = "agent.db"

    # Retrieval
    top_k: int = 5
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Server
    cors_origins: str = "*"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()