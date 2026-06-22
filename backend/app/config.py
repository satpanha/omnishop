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

    @field_validator("TELEGRAM_BOT_TOKEN", "TELEGRAM_WEBHOOK_SECRET", "JWT_SECRET_KEY", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip accidental leading/trailing whitespace from token values."""
        return v.strip() if isinstance(v, str) else v

    # ── JWT Auth ──────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # ── Instagram Integration ─────────────────────────────────
    INSTAGRAM_VERIFY_TOKEN: str = ""
    INSTAGRAM_APP_SECRET: str = ""
    INSTAGRAM_ACCESS_TOKEN: str = ""

    # ── Media / Image Uploads ─────────────────────────────────
    # When CLOUDINARY_URL is set (cloudinary://<key>:<secret>@<cloud>),
    # product photos are uploaded to Cloudinary. When empty, uploads fall
    # back to the local UPLOAD_DIR (suitable for local development only —
    # Render's filesystem is ephemeral and not safe for production media).
    CLOUDINARY_URL: str = ""
    CLOUDINARY_FOLDER: str = "omnishop/products"
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 5

    # ── App ───────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"
    ENVIRONMENT: str = "development"

    @field_validator("FRONTEND_URL", "ENVIRONMENT", mode="before")
    @classmethod
    def strip_url_whitespace(cls, v: str) -> str:
        """Strip accidental leading/trailing whitespace from URL/env values."""
        return v.strip() if isinstance(v, str) else v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (loaded once per process)."""
    return Settings()  # type: ignore[call-arg]