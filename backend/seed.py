"""
Seed script – populates the database with an initial product.

Usage:
    cd backend
    python seed.py
"""

import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.config import get_settings
from app.database import Base, async_session, engine
from app.models.product import Product
from app.models.seller import Seller


async def seed() -> None:
    settings = get_settings()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        stmt = select(Seller).where(Seller.telegram_id == settings.ADMIN_TELEGRAM_ID)
        result = await db.execute(stmt)
        seller = result.scalar_one_or_none()

        if not seller:
            seller = Seller(
                telegram_id=settings.ADMIN_TELEGRAM_ID,
                store_name="My OmniShop",
            )
            db.add(seller)
            await db.flush()

        product = Product(
            seller_id=seller.id,
            name="Classic T-Shirt",
            description="A comfortable 100% cotton classic t-shirt, available in multiple sizes.",
            price=Decimal("29.99"),
            stock_quantity=50,
            image_url="https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=800",
            is_active=True,
        )
        db.add(product)
        await db.commit()

    print(f"Seeded product: {product.name!r} (ID: {product.id})")
    


if __name__ == "__main__":
    asyncio.run(seed())
