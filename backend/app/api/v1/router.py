"""
OmniShop TMA API v1 Router.
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.orders import router as orders_router
from app.api.v1.products import router as products_router
from app.api.v1.transactions import router as transactions_router
from app.api.v1.webhooks import router as webhooks_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["Auth"])
router.include_router(products_router, prefix="/products", tags=["Products"])
router.include_router(orders_router, prefix="/orders", tags=["Orders"])
router.include_router(transactions_router, prefix="/transactions", tags=["Transactions"])
router.include_router(conversations_router, prefix="/conversations", tags=["Conversations"])
router.include_router(webhooks_router, prefix="/webhooks", tags=["Webhooks"])
