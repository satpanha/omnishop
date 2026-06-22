"""
Instagram Graph API Service.
Handles sending replies to Instagram DMs via Webhook triggers.
"""

import logging
import asyncio
import httpx
from typing import Any, Dict, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class InstagramService:
    """Service to interact with the Instagram Graph API (DMs)."""

    def __init__(self) -> None:
        settings = get_settings()
        self.access_token = settings.INSTAGRAM_ACCESS_TOKEN
        self.base_url = "https://graph.instagram.com/v18.0/me/messages"
        self.client = httpx.AsyncClient(timeout=10.0)

    async def send_reply(self, recipient_id: str, text: str, attempts: int = 3) -> bool:
        """Send a direct message response to an Instagram user."""
        if not self.access_token:
            logger.warning("Instagram Access Token is not set. Mocking DM send.")
            return True

        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": text},
        }
        params = {"access_token": self.access_token}

        for attempt in range(1, attempts + 1):
            try:
                response = await self.client.post(self.base_url, json=payload, params=params)
                response.raise_for_status()
                return True
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "Instagram Graph API HTTP error on attempt %d: %s - Response: %s",
                    attempt, exc, exc.response.text
                )
            except httpx.RequestError as exc:
                logger.error("Instagram Graph API Request error on attempt %d: %s", attempt, exc)

            if attempt < attempts:
                await asyncio.sleep(attempt * 1.5)

        return False

    async def close(self) -> None:
        """Clean up HTTP client resources."""
        await self.client.aclose()
