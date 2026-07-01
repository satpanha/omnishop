"""
Migration backfill test: existing Transactions are wrapped in synthetic Orders
without loss. Mirrors what the 0002_omnibot migration runs in production, but on
a synchronous SQLite engine so it executes in CI without Postgres.
"""

import uuid

from sqlalchemy import create_engine, text

import app.models  # noqa: F401 - register metadata
from app.database import Base
from app.db.backfill import backfill_orders


def _seed_legacy_rows(conn, statuses):
    sid, pid = str(uuid.uuid4()), str(uuid.uuid4())
    conn.execute(
        text(
            "INSERT INTO seller (id, created_at, updated_at, telegram_id, store_name) "
            "VALUES (:i,:t,:t,:tg,:n)"
        ),
        {"i": sid, "t": "2026-01-01 00:00:00", "tg": 555, "n": "S"},
    )
    conn.execute(
        text(
            "INSERT INTO product (id, created_at, updated_at, seller_id, name, price, "
            "stock_quantity, is_active) VALUES (:i,:t,:t,:s,:n,:p,:q,1)"
        ),
        {"i": pid, "t": "2026-01-01 00:00:00", "s": sid, "n": "P", "p": 10, "q": 5},
    )
    for st in statuses:
        conn.execute(
            text(
                'INSERT INTO "transaction" (id, created_at, updated_at, product_id, '
                "buyer_platform, buyer_id, quantity, total_price, status) "
                "VALUES (:i,:t,:t,:pid,:bp,:bi,:q,:tp,:s)"
            ),
            {
                "i": str(uuid.uuid4()),
                "t": "2026-01-01 00:00:00",
                "pid": pid,
                "bp": "telegram",
                "bi": "9",
                "q": 1,
                "tp": 10,
                "s": st,
            },
        )


def test_backfill_wraps_existing_transactions():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with engine.begin() as conn:
        _seed_legacy_rows(conn, ["pending", "paid", "cancelled"])

    with engine.begin() as conn:
        created = backfill_orders(conn)

    assert created == 3
    with engine.connect() as conn:
        orphans = conn.execute(
            text('SELECT count(*) FROM "transaction" WHERE order_id IS NULL')
        ).scalar()
        tx_total = conn.execute(text('SELECT count(*) FROM "transaction"')).scalar()
        statuses = dict(
            conn.execute(
                text('SELECT status, count(*) FROM "order" GROUP BY status')
            ).fetchall()
        )

    assert orphans == 0  # every transaction now has a parent order
    assert tx_total == 3  # nothing lost
    assert statuses == {"awaiting_payment": 1, "paid": 1, "cancelled": 1}


def test_backfill_is_idempotent():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        _seed_legacy_rows(conn, ["pending"])
    with engine.begin() as conn:
        assert backfill_orders(conn) == 1
    with engine.begin() as conn:
        # Second run finds nothing orphaned → creates nothing.
        assert backfill_orders(conn) == 0
