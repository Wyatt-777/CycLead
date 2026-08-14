"""Validated application configuration for local MVP execution."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a local .env file."""

    environment: str = "development"
    database_url: str = "sqlite:///data/cyclelead.db"
    qualification_threshold: int = Field(default=60, ge=0, le=100)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CYCLELEAD_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return one validated settings instance per process."""

    return Settings()
