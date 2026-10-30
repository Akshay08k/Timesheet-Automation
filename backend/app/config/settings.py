"""Application configuration settings using Pydantic Settings."""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = True

    # Security
    secret_key: str = "dev_secret_key_change_in_production_min_32_characters_long"
    pat_encryption_key: Optional[str] = None
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Database
    database_url: str = "sqlite:///./data/devtimesheet.db"

    # Gemini AI
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_fallback_model: str = "gemini-1.5-flash"

    # Azure DevOps Defaults
    default_client_org_url: str = "https://dev.azure.com/client-org"
    default_rysun_org_url: str = "https://dev.azure.com/rysun"

    # Default Timesheet Project Metadata
    default_client_name: str = "Visual Comfort and Co"
    default_iteration: str = "Rysun Project Management"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
