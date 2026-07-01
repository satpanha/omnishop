"""OmniBot: order aggregate, payment, conversation/message, delivery + backfill

Revision ID: 0002_omnibot
Revises: 0001_baseline
Create Date: 2026-06-30

Additive and backward-compatible:
  * creates order / payment / conversation / message
  * adds transaction.order_id (NULLABLE) + index + FK
  * adds seller.store_lat / store_lng / store_address
  * backfills every existing pending/paid/cancelled Transaction into a synthetic
    single-line Order (see app.db.backfill.backfill_orders)

``transaction.order_id`` is left NULLABLE on purpose: the application guarantees
new transactions always get an order_id (checkout + legacy /transactions both
create an Order), and the backfill sets it for old rows. To harden later — once
you've confirmed ``SELECT count(*) FROM "transaction" WHERE order_id IS NULL`` is
0 — uncomment the ``alter_column ... nullable=False`` block in upgrade().
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.db.backfill import backfill_orders

revision: str = "0002_omnibot"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _uuid_pk() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    # ── order (aggregate root) ────────────────────────────────
    op.create_table(
        "order",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("seller_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("buyer_platform", sa.String(length=20), nullable=False,
                  server_default="telegram"),
        sa.Column("buyer_id", sa.String(length=100), nullable=False),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("status", sa.String(length=20), nullable=False,
                  server_default="awaiting_payment"),
        sa.Column("delivery_address", sa.Text(), nullable=True),
        sa.Column("delivery_lat", sa.Numeric(9, 6), nullable=True),
        sa.Column("delivery_lng", sa.Numeric(9, 6), nullable=True),
        sa.Column("distance_km", sa.Numeric(6, 2), nullable=True),
        sa.Column("eta_minutes", sa.Integer(), nullable=True),
        sa.Column("dispatch_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_order"),
        sa.ForeignKeyConstraint(["seller_id"], ["seller.id"],
                                name="fk_order_seller_id_seller", ondelete="RESTRICT"),
        sa.UniqueConstraint("idempotency_key", name="uq_order_idempotency_key"),
        sa.CheckConstraint("total_amount >= 0", name="ck_order_order_total_non_negative"),
        sa.CheckConstraint(
            "status IN ('awaiting_payment','paid','preparing','dispatched',"
            "'delivered','cancelled','payment_expired')",
            name="ck_order_order_status_valid",
        ),
    )
    op.create_index("ix_order_seller_id", "order", ["seller_id"])
    op.create_index("ix_order_buyer_id", "order", ["buyer_id"])
    op.create_index("ix_order_status", "order", ["status"])

    # ── payment (1:1 with order) ──────────────────────────────
    op.create_table(
        "payment",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False,
                  server_default="aba_payway"),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("khqr_string", sa.Text(), nullable=True),
        sa.Column("aba_link", sa.String(length=500), nullable=True),
        sa.Column("provider_txn_ref", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="initiated"),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_callback", postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_payment"),
        sa.ForeignKeyConstraint(["order_id"], ["order.id"],
                                name="fk_payment_order_id_order", ondelete="CASCADE"),
        sa.UniqueConstraint("order_id", name="uq_payment_order_id"),
        sa.UniqueConstraint("provider_txn_ref", name="uq_payment_provider_txn_ref"),
        sa.CheckConstraint("amount >= 0", name="ck_payment_payment_amount_non_negative"),
        sa.CheckConstraint("status IN ('initiated','paid','failed','expired')",
                           name="ck_payment_payment_status_valid"),
    )
    op.create_index("ix_payment_order_id", "payment", ["order_id"])
    op.create_index("ix_payment_provider_txn_ref", "payment", ["provider_txn_ref"])

    # ── conversation ──────────────────────────────────────────
    op.create_table(
        "conversation",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("buyer_platform", sa.String(length=20), nullable=False),
        sa.Column("buyer_id", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False, server_default="bot"),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_conversation"),
        sa.UniqueConstraint("buyer_platform", "buyer_id",
                            name="conversation_platform_buyer"),
        sa.CheckConstraint(
            "state IN ('bot','awaiting_owner','owner_handling','closed')",
            name="ck_conversation_conversation_state_valid",
        ),
    )
    op.create_index("ix_conversation_buyer_id", "conversation", ["buyer_id"])
    op.create_index("ix_conversation_last_message_at", "conversation", ["last_message_at"])

    # ── message ───────────────────────────────────────────────
    op.create_table(
        "message",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("sender", sa.String(length=10), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("telegram_message_id", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_message"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversation.id"],
                                name="fk_message_conversation_id_conversation",
                                ondelete="CASCADE"),
        sa.CheckConstraint("direction IN ('inbound','outbound')",
                           name="ck_message_message_direction_valid"),
        sa.CheckConstraint("sender IN ('buyer','owner','bot')",
                           name="ck_message_message_sender_valid"),
    )
    op.create_index("ix_message_conversation_id", "message", ["conversation_id"])

    # ── alter transaction: add order_id (nullable for backfill) ─
    op.add_column(
        "transaction",
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_transaction_order_id_order", "transaction", "order",
        ["order_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index("ix_transaction_order_id", "transaction", ["order_id"])

    # ── alter seller: store origin for delivery ETA ───────────
    op.add_column("seller", sa.Column("store_lat", sa.Numeric(9, 6), nullable=True))
    op.add_column("seller", sa.Column("store_lng", sa.Numeric(9, 6), nullable=True))
    op.add_column("seller", sa.Column("store_address", sa.Text(), nullable=True))

    # ── data backfill ─────────────────────────────────────────
    backfill_orders(op.get_bind())

    # Once order_id IS NULL count == 0 in prod, you may enforce NOT NULL:
    # op.alter_column("transaction", "order_id", nullable=False)


def downgrade() -> None:
    op.drop_column("seller", "store_address")
    op.drop_column("seller", "store_lng")
    op.drop_column("seller", "store_lat")
    op.drop_index("ix_transaction_order_id", table_name="transaction")
    op.drop_constraint("fk_transaction_order_id_order", "transaction", type_="foreignkey")
    op.drop_column("transaction", "order_id")
    op.drop_table("message")
    op.drop_table("conversation")
    op.drop_table("payment")
    op.drop_table("order")
