"""baseline schema (pre-OmniBot): seller, product, transaction, auto_response

Revision ID: 0001_baseline
Revises:
Create Date: 2026-06-30

This is the first real Alembic migration. It captures the schema that previously
existed only via ``Base.metadata.create_all``.

For a DATABASE THAT ALREADY HAS THESE TABLES (created by create_all), do NOT run
this migration — instead baseline it with:  ``alembic stamp 0001_baseline``
and then run ``alembic upgrade head`` to apply the OmniBot feature migration.
For a fresh database, ``alembic upgrade head`` creates everything.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_baseline"
down_revision: str | None = None
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
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    # ── seller ────────────────────────────────────────────────
    op.create_table(
        "seller",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("ig_business_id", sa.String(), nullable=True),
        sa.Column("store_name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_seller"),
        sa.UniqueConstraint("telegram_id", name="uq_seller_telegram_id"),
    )
    op.create_index("ix_seller_telegram_id", "seller", ["telegram_id"])

    # ── product ───────────────────────────────────────────────
    op.create_table(
        "product",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("seller_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("stock_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id", name="pk_product"),
        sa.ForeignKeyConstraint(
            ["seller_id"], ["seller.id"],
            name="fk_product_seller_id_seller", ondelete="CASCADE",
        ),
        sa.CheckConstraint("stock_quantity >= 0", name="ck_product_stock_non_negative"),
    )
    op.create_index("ix_product_seller_id", "product", ["seller_id"])
    op.create_index("ix_product_name", "product", ["name"])

    # ── transaction ───────────────────────────────────────────
    op.create_table(
        "transaction",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("buyer_platform", sa.String(length=20), nullable=False),
        sa.Column("buyer_id", sa.String(length=100), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("total_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.PrimaryKeyConstraint("id", name="pk_transaction"),
        sa.ForeignKeyConstraint(
            ["product_id"], ["product.id"],
            name="fk_transaction_product_id_product", ondelete="CASCADE",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_transaction_quantity_positive"),
    )
    op.create_index("ix_transaction_product_id", "transaction", ["product_id"])

    # ── auto_response ─────────────────────────────────────────
    op.create_table(
        "auto_response",
        _uuid_pk(),
        *_timestamps(),
        sa.Column("seller_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("keyword", sa.String(length=100), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_auto_response"),
        sa.ForeignKeyConstraint(
            ["seller_id"], ["seller.id"],
            name="fk_auto_response_seller_id_seller", ondelete="CASCADE",
        ),
    )
    op.create_index("ix_auto_response_seller_id", "auto_response", ["seller_id"])
    op.create_index("ix_auto_response_keyword", "auto_response", ["keyword"])


def downgrade() -> None:
    op.drop_table("auto_response")
    op.drop_table("transaction")
    op.drop_table("product")
    op.drop_table("seller")
