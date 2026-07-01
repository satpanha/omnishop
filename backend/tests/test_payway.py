"""Unit tests for the ABA PayWay service (HMAC verify + stub purchase)."""

import pytest

from app.services.payway import PayWayService


def test_verify_callback_good_signature():
    body = b'{"tran_id":"abc","status":"success"}'
    secret = "s3cr3t"
    sig = PayWayService.compute_signature(body, secret)
    assert PayWayService.verify_callback(body, sig, secret) is True


def test_verify_callback_bad_signature():
    body = b'{"tran_id":"abc"}'
    assert PayWayService.verify_callback(body, "deadbeef", "s3cr3t") is False


def test_verify_callback_missing_signature_or_secret():
    body = b"{}"
    assert PayWayService.verify_callback(body, None, "s3cr3t") is False
    assert PayWayService.verify_callback(body, "x", "") is False


def test_verify_callback_tamper_changes_signature():
    secret = "s3cr3t"
    sig = PayWayService.compute_signature(b'{"amount":"10.00"}', secret)
    # Same signature must NOT validate a tampered body.
    assert PayWayService.verify_callback(b'{"amount":"99.00"}', sig, secret) is False


@pytest.mark.asyncio
async def test_stub_purchase_is_deterministic():
    svc = PayWayService()
    assert svc.configured is False  # no creds in tests → stub
    r1 = await svc.create_purchase(order_id="order-1", amount="20.00", currency="USD")
    r2 = await svc.create_purchase(order_id="order-1", amount="20.00", currency="USD")
    assert r1.provider_txn_ref == "STUB-order-1" == r2.provider_txn_ref
    assert r1.khqr_string and r1.aba_link
    assert r1.status == "initiated"
