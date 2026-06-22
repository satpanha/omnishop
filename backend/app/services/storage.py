"""
Image storage service.

Abstracts where uploaded product photos live:

  * **Production** – when ``CLOUDINARY_URL`` is configured, files are uploaded
    to Cloudinary and the returned ``secure_url`` is persisted on the product.
    Cloudinary serves the image from its CDN, so nothing is stored on the
    (ephemeral) application server.

  * **Development** – when no cloud provider is configured, files are written
    to ``UPLOAD_DIR`` and served by FastAPI's StaticFiles mount at ``/uploads``.
    This is convenient locally but must NOT be relied on in production because
    Render wipes the local filesystem on every deploy.

The public entrypoint is :func:`save_image`, which is synchronous (Cloudinary's
SDK and local disk writes both block) and is therefore expected to be called via
``fastapi.concurrency.run_in_threadpool`` from request handlers.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from urllib.parse import urlparse

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Allowed image MIME types mapped to the extension used when saving locally.
ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

MAX_UPLOAD_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

# ── Cloudinary initialisation (only when configured) ──────────────────────────
_CLOUDINARY_ENABLED = bool(settings.CLOUDINARY_URL)

if _CLOUDINARY_ENABLED:
    # Configure the SDK explicitly from the parsed URL rather than relying on it
    # reading the CLOUDINARY_URL env var. pydantic-settings loads the value from
    # .env without exporting it to os.environ, and the SDK only auto-reads the
    # env var the first time it is configured — so the result would otherwise
    # depend on import order. Parsing here makes it deterministic.
    # Format: cloudinary://<api_key>:<api_secret>@<cloud_name>
    _parsed = urlparse(settings.CLOUDINARY_URL)
    import cloudinary  # noqa: E402  (import guarded by configuration)

    cloudinary.config(
        cloud_name=_parsed.hostname,
        api_key=_parsed.username,
        api_secret=_parsed.password,
        secure=True,
    )
    logger.info("Storage backend: Cloudinary (cloud=%s)", cloudinary.config().cloud_name)
else:
    logger.warning(
        "Storage backend: local disk (%s). Set CLOUDINARY_URL for production.",
        settings.UPLOAD_DIR,
    )


def is_remote() -> bool:
    """Return True when uploads go to a remote provider (Cloudinary)."""
    return _CLOUDINARY_ENABLED


def save_image(data: bytes, content_type: str, request_base_url: str) -> str:
    """
    Persist image ``data`` and return a publicly accessible URL.

    Args:
        data: Raw image bytes (already validated for type/size by the caller).
        content_type: The MIME type, used to pick the correct file extension.
        request_base_url: Absolute base URL of the incoming request
            (e.g. ``http://localhost:8000/``), used to build the public URL
            for the local-disk fallback. Ignored by remote providers.

    Returns:
        The public URL to store on the product record.
    """
    extension = ALLOWED_CONTENT_TYPES.get(content_type, "")

    if _CLOUDINARY_ENABLED:
        import cloudinary.uploader

        result = cloudinary.uploader.upload(
            data,
            folder=settings.CLOUDINARY_FOLDER,
            resource_type="image",
        )
        return result["secure_url"]

    # ── Local-disk fallback (development) ─────────────────────────────────────
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4().hex}{extension}"
    (upload_dir / filename).write_bytes(data)

    return f"{request_base_url.rstrip('/')}/uploads/{filename}"
