"""
Integration tests for the Orders API + ABA PayWay callback (primary flow).
"""

import json
from datetime import timedelta

import pytest
from httpx import AsyncClient

from app.auth.jwt_handler import create_access_token
from app.config import get_settings
from app.services.payway import PayWayService

OTHER_BUYER_SUB = "5555555555"


def _other_buyer_token() -> str:
    return create_access_token({"sub": OTHER_BUYER_SUB, "role": "buyer"},
                               expires_delta=timedelta(minutes=10))


async def _create_product(client, admin_token, *, price="10.00", stock=100):
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await client.post(
        "/api/v1/products",
        json={"name": "Widget", "price": price, "stock_quantity": stock},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_order(client, buyer_token, product_id, qty=2, key="k1"):
    headers = {"Authorization": f"Bearer {buyer_token}"}
    return await client.post(
        "/api/v1/orders",
        json={
            "items": [{"product_id": product_id, "quantity": qty}],
            "delivery": {"lat": 11.5564, "lng": 104.9282, "address": "Phnom Penh"},
            "idempotency_key": key,
        },
        headers=headers,
    )


@pytest.mark.asyncio
async def test_create_order_returns_payment_and_decrements_stock(
    client: AsyncClient, mock_admin_token, mock_buyer_token
):
    product = await _create_product(client, mock_admin_token, price="10.00", stock=100)
    resp = await _create_order(client, mock_buyer_token, product["id"], qty=2)
    assert resp.status_code == 201, resp.text
    order = resp.json()

    assert order["status"] == "awaiting_payment"
    assert order["total_amount"] == "20.00"
    assert len(order["line_items"]) == 1
    assert order["payment"] is not None
    assert order["payment"]["khqr_string"]
    assert order["payment"]["aba_link"]
    assert order["eta_minutes"] is not None  # delivery coords → ETA computed

    # stock decremented 100 → 98
    prod = (await client.get(f"/api/v1/products/{product['id']}")).json()
    assert prod["stock_quantity"] == 98


@pytest.mark.asyncio
async def test_create_order_is_idempotent(client, mock_admin_token, mock_buyer_token):
    product = await _create_product(client, mock_admin_token, stock=100)
    r1 = await _create_order(client, mock_buyer_token, product["id"], qty=2, key="dupe")
    r2 = await _create_order(client, mock_buyer_token, product["id"], qty=2, key="dupe")
    assert r1.json()["id"] == r2.json()["id"]
    # stock only decremented once
    prod = (await client.get(f"/api/v1/products/{product['id']}")).json()
    assert prod["stock_quantity"] == 98


@pytest.mark.asyncio
async def test_insufficient_stock_rejected(client, mock_admin_token, mock_buyer_token):
    product = await _create_product(client, mock_admin_token, stock=1)
    resp = await _create_order(client, mock_buyer_token, product["id"], qty=5)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_order_access_control(client, mock_admin_token, mock_buyer_token):
    product = await _create_product(client, mock_admin_token)
    order = (await _create_order(client, mock_buyer_token, product["id"])).json()

    # owning buyer can read
    own = await client.get(
        f"/api/v1/orders/{order['id']}",
        headers={"Authorization": f"Bearer {mock_buyer_token}"},
    )
    assert own.status_code == 200
    assert own.headers["cache-control"] == "no-store"

    # a different buyer cannot
    other = await client.get(
        f"/api/v1/orders/{order['id']}",
        headers={"Authorization": f"Bearer {_other_buyer_token()}"},
    )
    assert other.status_code == 403

    # admin can
    adm = await client.get(
        f"/api/v1/orders/{order['id']}",
        headers={"Authorization": f"Bearer {mock_admin_token}"},
    )
    assert adm.status_code == 200


@pytest.mark.asyncio
async def test_list_orders_admin_only(client, mock_admin_token, mock_buyer_token):
    product = await _create_product(client, mock_admin_token)
    await _create_order(client, mock_buyer_token, product["id"])

    buyer = await client.get(
        "/api/v1/orders", headers={"Authorization": f"Bearer {mock_buyer_token}"}
    )
    assert buyer.status_code == 403

    admin = await client.get(
        "/api/v1/orders", headers={"Authorization": f"Bearer {mock_admin_token}"}
    )
    assert admin.status_code == 200
    assert admin.json()["total"] >= 1


@pytest.mark.asyncio
async def test_illegal_status_transition_conflicts(client, mock_admin_token, mock_buyer_token):
    product = await _create_product(client, mock_admin_token)
    order = (await _create_order(client, mock_buyer_token, product["id"])).json()
    # awaiting_payment → delivered is illegal
    resp = await client.patch(
        f"/api/v1/orders/{order['id']}/status",
        json={"status": "delivered"},
        headers={"Authorization": f"Bearer {mock_admin_token}"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_cancel_restocks(client, mock_admin_token, mock_buyer_token):
    product = await _create_product(client, mock_admin_token, stock=10)
    order = (await _create_order(client, mock_buyer_token, product["id"], qty=3)).json()
    # stock 10 → 7
    prod = (await client.get(f"/api/v1/products/{product['id']}")).json()
    assert prod["stock_quantity"] == 7

    resp = await client.patch(
        f"/api/v1/orders/{order['id']}/status",
        json={"status": "cancelled"},
        headers={"Authorization": f"Bearer {mock_admin_token}"},
    )
    assert resp.status_code == 200
    prod = (await client.get(f"/api/v1/products/{product['id']}")).json()
    assert prod["stock_quantity"] == 10  # restocked


# ── ABA PayWay callback (source of truth) ────────────────────────────────

def _signed_callback(order_id, status_value="success"):
    secret = get_settings().ABA_PAYWAY_CALLBACK_SECRET
    body = json.dumps(
        {"tran_id": f"STUB-{order_id}", "status": status_value}
    ).encode("utf-8")
    sig = PayWayService.compute_signature(body, secret)
    return body, sig


@pytest.mark.asyncio
async def test_payway_callback_settles_order(client, mock_admin_token, mock_buyer_token):
    product = await _create_product(client, mock_admin_token)
    order = (await _create_order(client, mock_buyer_token, product["id"])).json()

    body, sig = _signed_callback(order["id"])
    resp = await client.post(
        "/api/v1/webhooks/payway",
        content=body,
        headers={"X-Payway-Signature": sig, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    got = (
        await client.get(
            f"/api/v1/orders/{order['id']}",
            headers={"Authorization": f"Bearer {mock_admin_token}"},
        )
    ).json()
    assert got["status"] == "paid"
    assert got["payment"]["status"] == "paid"


@pytest.mark.asyncio
async def test_payway_callback_is_idempotent(client, mock_admin_token, mock_buyer_token):
    product = await _create_product(client, mock_admin_token)
    order = (await _create_order(client, mock_buyer_token, product["id"])).json()
    body, sig = _signed_callback(order["id"])
    headers = {"X-Payway-Signature": sig, "Content-Type": "application/json"}

    first = await client.post("/api/v1/webhooks/payway", content=body, headers=headers)
    second = await client.post("/api/v1/webhooks/payway", content=body, headers=headers)
    assert first.status_code == 200 and second.status_code == 200

    got = (
        await client.get(
            f"/api/v1/orders/{order['id']}",
            headers={"Authorization": f"Bearer {mock_admin_token}"},
        )
    ).json()
    assert got["status"] == "paid"  # still paid, no double-processing error


@pytest.mark.asyncio
async def test_payway_callback_rejects_bad_signature(client, mock_admin_token, mock_buyer_token):
    product = await _create_product(client, mock_admin_token)
    order = (await _create_order(client, mock_buyer_token, product["id"])).json()
    body, _ = _signed_callback(order["id"])
    resp = await client.post(
        "/api/v1/webhooks/payway",
        content=body,
        headers={"X-Payway-Signature": "forged", "Content-Type": "application/json"},
    )
    assert resp.status_code == 401
    # order remains unpaid
    got = (
        await client.get(
            f"/api/v1/orders/{order['id']}",
            headers={"Authorization": f"Bearer {mock_admin_token}"},
        )
    ).json()
    assert got["status"] == "awaiting_payment"


@pytest.mark.asyncio
async def test_payway_callback_unknown_reference_ignored(client):
    body = json.dumps({"tran_id": "STUB-does-not-exist", "status": "success"}).encode()
    sig = PayWayService.compute_signature(body, get_settings().ABA_PAYWAY_CALLBACK_SECRET)
    resp = await client.post(
        "/api/v1/webhooks/payway",
        content=body,
        headers={"X-Payway-Signature": sig, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
