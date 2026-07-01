"""
ABA PayWay payment service.

Generates a purchase (returning a KHQR payload + an ABA deep link) and verifies
the HMAC signature on the server-to-server payment callback.

Two modes:
  * **Live** — when ``settings.aba_payway_configured`` is True, calls the ABA
    PayWay API. (The exact request contract depends on your merchant onboarding;
    the call site is marked and isolated so you can fill in field names without
    touching the rest of the feature.)
  * **Stub** — when credentials are absent (dev / tests), returns deterministic
    values so the whole flow is exercisable offline. Stub purchases are never
    auto-marked paid; payment still arrives via the callback (or the reconcile/
    manual path), keeping the webhook-as-source-of-truth invariant intact.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class PurchaseResult:
    provider: str
    provider_txn_ref: str
    khqr_string: str | None
    aba_link: str | None
    status: str  # 'initiated' | 'failed'


class PayWayService:
    """Interact with ABA PayWay (or a deterministic stub when unconfigured)."""

    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.configured = settings.aba_payway_configured
        self.base_url = settings.ABA_PAYWAY_BASE_URL.rstrip("/")
        self.merchant_id = settings.ABA_PAYWAY_MERCHANT_ID
        self.api_key = settings.ABA_PAYWAY_API_KEY

    async def create_purchase(
        self, *, order_id: str, amount: str, currency: str
    ) -> PurchaseResult:
        """Create a payment intent and return the QR / link the buyer pays with."""
        if not self.configured:
            return self._stub_purchase(order_id=order_id, amount=amount, currency=currency)

        # ── Live ABA PayWay call ──────────────────────────────
        # NOTE: field names below are placeholders to be confirmed against your
        # PayWay merchant integration guide. Isolated here on purpose.
        payload = {
            "merchant_id": self.merchant_id,
            "tran_id": order_id,
            "amount": amount,
            "currency": currency,
        }
        payload["hash"] = self._request_hash(payload)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/payment-gateway/v1/payments/purchase",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
            return PurchaseResult(
                provider="aba_payway",
                provider_txn_ref=str(data.get("tran_id", order_id)),
                khqr_string=data.get("qrString"),
                aba_link=data.get("abapay_deeplink") or data.get("checkout_url"),
                status="initiated",
            )
        except Exception as exc:  # noqa: BLE001 - surface as failed, caller falls back
            logger.error("ABA PayWay purchase failed for order %s: %s", order_id, exc)
            return PurchaseResult(
                provider="aba_payway",
                provider_txn_ref=order_id,
                khqr_string=None,
                aba_link=None,
                status="failed",
            )

    def _stub_purchase(
        self, *, order_id: str, amount: str, currency: str
    ) -> PurchaseResult:
        """Deterministic offline purchase for dev/tests."""
        return PurchaseResult(
            provider="aba_payway",
            provider_txn_ref=f"STUB-{order_id}",
            khqr_string=f"00020101021229{order_id}5204{amount}5303{currency}",
            aba_link=f"{self.base_url}/pay/{order_id}",
            status="initiated",
        )

    def _request_hash(self, payload: dict[str, str]) -> str:
        """HMAC-SHA512 over the concatenated request fields (ABA convention)."""
        message = "".join(
            str(payload[k]) for k in ("merchant_id", "tran_id", "amount", "currency")
        )
        return hmac.new(
            self.api_key.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha512,
        ).hexdigest()

    # ── Callback signature verification (source of truth) ─────
    @staticmethod
    def compute_signature(raw_body: bytes, secret: str) -> str:
        """HMAC-SHA512 hex of the raw callback body."""
        return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()

    @classmethod
    def verify_callback(cls, raw_body: bytes, signature: str | None, secret: str) -> bool:
        """
        Constant-time verify of a callback signature. Returns False on any missing
        input so an unsigned/spoofed callback can never advance payment state.
        """
        if not signature or not secret:
            return False
        expected = cls.compute_signature(raw_body, secret)
        return hmac.compare_digest(expected, signature)
