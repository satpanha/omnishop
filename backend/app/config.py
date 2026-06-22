"""
Application configuration using pydantic-settings.
All settings are loaded from environment variables or a .env file.
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the OmniShop TMA backend."""

    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str

    @field_validator("DATABASE_URL")
    @classmethod
    def sanitize_database_url(cls, v: str) -> str:
        # Check scheme
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
            
        # Replace sslmode with ssl for asyncpg compatibility
        if "sslmode=" in v:
            v = v.replace("sslmode=require", "ssl=require")
            v = v.replace("sslmode=prefer", "ssl=prefer")
            v = v.replace("sslmode=disable", "ssl=disable")
            v = v.replace("sslmode=allow", "ssl=allow")
        return v

    # ── Telegram Bot ──────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_WEBHOOK_SECRET: str
    ADMIN_TELEGRAM_ID: int

    # ── JWT Auth ──────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # ── Instagram Integration ─────────────────────────────────
    INSTAGRAM_VERIFY_TOKEN: str = ""
    INSTAGRAM_APP_SECRET: str = ""
    INSTAGRAM_ACCESS_TOKEN: str = ""

    # ── App ───────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"
    ENVIRONMENT: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (loaded once per process)."""
    return Settings()  # type: ignore[call-arg]
