"""
Import all models so Alembic (and SQLAlchemy metadata) can discover them.
"""

from app.models.auto_response import AutoResponse  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.seller import Seller  # noqa: F401
from app.models.transaction import Transaction  # noqa: F401

__all__ = ["AutoResponse", "Product", "Seller", "Transaction"]
