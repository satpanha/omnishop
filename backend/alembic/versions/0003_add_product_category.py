"""add category column to product

Revision ID: 0003_add_product_category
Revises: 0002_omnibot
Create Date: 2026-09-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_add_product_category"
down_revision: str | None = "0002_omnibot"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "product",
        sa.Column("category", sa.String(length=50), nullable=True),
    )
    op.create_index("ix_product_category", "product", ["category"])


def downgrade() -> None:
    op.drop_index("ix_product_category", table_name="product")
    op.drop_column("product", "category")
