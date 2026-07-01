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

    @field_validator(
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_WEBHOOK_SECRET",
        "JWT_SECRET_KEY",
        "ABA_PAYWAY_API_KEY",
        "ABA_PAYWAY_CALLBACK_SECRET",
        mode="before",
    )
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

    # ── OmniBot: Payments (ABA PayWay) ────────────────────────
    # Master feature flag. When False, checkout uses the legacy "manual payment
    # verification" flow and no payment/order automation runs — so the feature
    # can be shipped dark and enabled without a redeploy.
    PAYMENTS_ENABLED: bool = False
    # ABA PayWay credentials. When any are blank the PayWay service runs in a
    # deterministic STUB mode (safe for dev/tests); production must set all three.
    ABA_PAYWAY_BASE_URL: str = "https://checkout.payway.com.kh"
    ABA_PAYWAY_MERCHANT_ID: str = ""
    ABA_PAYWAY_API_KEY: str = ""
    # Shared secret used to verify the HMAC signature on PayWay callbacks.
    ABA_PAYWAY_CALLBACK_SECRET: str = ""
    PAYMENT_CURRENCY: str = "USD"
    # How long an order may sit in awaiting_payment before it auto-expires.
    PAYMENT_TTL_MINUTES: int = 30

    # ── OmniBot: Delivery / ETA estimation ────────────────────
    # Average effective delivery speed (km/h) used by the haversine ETA fallback.
    DELIVERY_SPEED_KMH: float = 20.0
    # Fixed prep time added to travel time for the ETA estimate.
    DELIVERY_BASE_PREP_MINUTES: int = 15

    # ── App ───────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"
    ENVIRONMENT: str = "development"

    @field_validator("FRONTEND_URL", "ENVIRONMENT", mode="before")
    @classmethod
    def strip_url_whitespace(cls, v: str) -> str:
        """Strip accidental leading/trailing whitespace from URL/env values."""
        return v.strip() if isinstance(v, str) else v

    @property
    def aba_payway_configured(self) -> bool:
        """True when live ABA PayWay credentials are present (else stub mode)."""
        return bool(
            self.ABA_PAYWAY_MERCHANT_ID
            and self.ABA_PAYWAY_API_KEY
            and self.ABA_PAYWAY_CALLBACK_SECRET
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (loaded once per process)."""
    return Settings()  # type: ignore[call-arg]