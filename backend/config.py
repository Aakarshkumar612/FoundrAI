"""Application settings loaded from environment variables via pydantic-settings."""

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    # Groq
    groq_api_key: str = ""

    # News
    newscatcher_api_key: str = ""

    # Superset
    superset_url: str = "http://localhost:8088"
    superset_username: str = "admin"
    superset_password: str = ""
    superset_guest_token_jwt_secret: str = ""

    # App config
    environment: str = "development"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    log_level: str = "INFO"
    max_upload_size_bytes: int = 10_485_760  # 10MB
    port: int = 8000

    # Feature flags
    enable_news_scheduler: bool = True
    enable_autogluon_fallback: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str) -> str:
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance — parsed once at startup."""
    return Settings()
