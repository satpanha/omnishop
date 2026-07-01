"""
Data backfill: wrap pre-existing Transactions in synthetic single-line Orders.

Before the OmniBot feature, each cart item was a standalone ``Transaction`` with
no parent ``Order``. This helper creates one Order per orphaned Transaction so the
new aggregate-based flow (and the NOT-NULL-able ``order_id`` going forward) has a
consistent history.

It is intentionally **dialect-agnostic** (Core ``text()`` + Python-generated
UUIDs, no ``gen_random_uuid()``) so the exact same routine runs inside the Alembic
migration (Postgres) and inside the unit test (SQLite). ``"order"`` and
``"transaction"`` are quoted because both are reserved words.
"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.engine import Connection

# Legacy transaction.status → new order.status
_STATUS_MAP = {
    "pending": "awaiting_payment",
    "paid": "paid",
    "cancelled": "cancelled",
}


def backfill_orders(bind: Connection) -> int:
    """
    Create a synthetic Order for every Transaction whose ``order_id`` is NULL.

    Args:
        bind: a synchronous SQLAlchemy Connection (e.g. ``op.get_bind()`` in a
            migration, or a plain engine connection in tests).

    Returns:
        The number of orders created (== transactions backfilled).
    """
    rows = bind.execute(
        text(
            """
            SELECT t.id AS tx_id,
                   t.buyer_platform AS buyer_platform,
                   t.buyer_id AS buyer_id,
                   t.total_price AS total_price,
                   t.status AS status,
                   t.created_at AS created_at,
                   t.updated_at AS updated_at,
                   p.seller_id AS seller_id
            FROM "transaction" t
            JOIN product p ON p.id = t.product_id
            WHERE t.order_id IS NULL
            """
        )
    ).fetchall()

    created = 0
    for r in rows:
        order_id = uuid.uuid4()
        bind.execute(
            text(
                """
                INSERT INTO "order"
                    (id, seller_id, buyer_platform, buyer_id, total_amount,
                     currency, status, created_at, updated_at)
                VALUES
                    (:id, :seller_id, :buyer_platform, :buyer_id, :total_amount,
                     :currency, :status, :created_at, :updated_at)
                """
            ),
            {
                "id": str(order_id),
                "seller_id": str(r.seller_id),
                "buyer_platform": r.buyer_platform,
                "buyer_id": r.buyer_id,
                "total_amount": r.total_price,
                "currency": "USD",
                "status": _STATUS_MAP.get(r.status, "awaiting_payment"),
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            },
        )
        bind.execute(
            text('UPDATE "transaction" SET order_id = :oid WHERE id = :tid'),
            {"oid": str(order_id), "tid": str(r.tx_id)},
        )
        created += 1

    return created
