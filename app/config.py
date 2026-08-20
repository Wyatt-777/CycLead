"""Validated application configuration for local MVP execution."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a local .env file."""

    environment: str = "development"
    database_url: str = "sqlite:///data/cyclelead.db"
    qualification_threshold: int = Field(default=60, ge=0, le=100)
    brave_search_api_key: SecretStr | None = None
    brave_search_country: str = Field(default="US", min_length=2, max_length=2)
    brave_search_language: str = Field(default="en", min_length=2, max_length=32)
    brave_search_result_count: int = Field(default=10, ge=1, le=20)
    brave_search_timeout_seconds: float = Field(default=10, gt=0, le=60)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CYCLELEAD_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return one validated settings instance per process."""

    return Settings()
