"""
Telegram Bot API Service.
Handles sending out-of-band messages/photos to Telegram users/admin.
"""

import logging
import asyncio
import httpx
from typing import Any, Dict, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class TelegramService:
    """Service to interact with the Telegram Bot API."""

    def __init__(self) -> None:
        settings = get_settings()
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.client = httpx.AsyncClient(timeout=10.0)

    async def _post_with_retry(self, endpoint: str, json_data: Dict[str, Any], attempts: int = 3) -> Optional[Dict[str, Any]]:
        """Perform a POST request with simple backoff retry logic."""
        url = f"{self.base_url}/{endpoint}"
        for attempt in range(1, attempts + 1):
            try:
                response = await self.client.post(url, json=json_data)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "Telegram API HTTP error on attempt %d: %s - Response: %s",
                    attempt, exc, exc.response.text
                )
            except httpx.RequestError as exc:
                logger.error("Telegram API Request error on attempt %d: %s", attempt, exc)
            
            if attempt < attempts:
                await asyncio.sleep(attempt * 1.5)
        return None

    async def send_message(
        self,
        chat_id: int | str,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send a text message to a user/chat, optionally with an inline keyboard."""
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        res = await self._post_with_retry("sendMessage", payload)
        return res is not None and res.get("ok") is True

    async def send_photo(
        self,
        chat_id: int | str,
        photo_url: str,
        caption: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send a photo with a caption to a user/chat, optionally with a keyboard."""
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption,
            "parse_mode": parse_mode,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        res = await self._post_with_retry("sendPhoto", payload)
        return res is not None and res.get("ok") is True

    async def answer_callback_query(
        self, callback_query_id: str, text: Optional[str] = None
    ) -> bool:
        """Acknowledge an inline-button press so the client stops its spinner."""
        payload: Dict[str, Any] = {"callback_query_id": callback_query_id}
        if text is not None:
            payload["text"] = text
        res = await self._post_with_retry("answerCallbackQuery", payload)
        return res is not None and res.get("ok") is True

    @staticmethod
    def inline_keyboard(buttons: list[list[Dict[str, str]]]) -> Dict[str, Any]:
        """Build a Telegram inline_keyboard reply_markup from rows of buttons.

        Each button is a dict like ``{"text": "View", "callback_data": "order:..:view"}``
        or ``{"text": "Pay", "url": "https://.."}``.
        """
        return {"inline_keyboard": buttons}

    async def close(self) -> None:
        """Clean up HTTP client resources."""
        await self.client.aclose()
