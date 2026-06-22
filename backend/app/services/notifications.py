"""
Admin Notification Service.
Sends alerts about transactions or inventory status directly to the seller's Telegram account.
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.product import Product
from app.models.transaction import Transaction
from app.services.telegram import TelegramService

logger = logging.getLogger(__name__)


async def notify_new_order(db: AsyncSession, transaction: Transaction, product: Product) -> None:
    """Send an order receipt notification to the admin via Telegram."""
    settings = get_settings()
    admin_id = settings.ADMIN_TELEGRAM_ID
    
    if not admin_id:
        logger.warning("ADMIN_TELEGRAM_ID is not configured. Skipping order notification.")
        return

    # Format notification text
    msg = (
        f"<b>🛒 New Order Received!</b>\n\n"
        f"<b>Product:</b> {product.name}\n"
        f"<b>Quantity:</b> {transaction.quantity}\n"
        f"<b>Total Price:</b> ${transaction.total_price:.2f}\n"
        f"<b>Platform:</b> {transaction.buyer_platform.capitalize()}\n"
        f"<b>Buyer ID:</b> <code>{transaction.buyer_id}</code>\n"
        f"<b>Order ID:</b> <code>{transaction.id}</code>\n\n"
        f"<i>Status: {transaction.status}</i>"
    )

    telegram = TelegramService()
    try:
        success = await telegram.send_message(chat_id=admin_id, text=msg)
        if success:
            logger.info("Admin notified of new transaction: %s", transaction.id)
        else:
            logger.error("Failed to send order notification to admin.")

        # Check if product stock has dropped below alert threshold (e.g., 5)
        if product.stock_quantity < 5:
            await notify_low_stock(product)
            
    except Exception as exc:
        logger.error("Error in notify_new_order: %s", exc)
    finally:
        await telegram.close()


async def notify_low_stock(product: Product) -> None:
    """Alert the admin that a product's inventory is low."""
    settings = get_settings()
    admin_id = settings.ADMIN_TELEGRAM_ID

    if not admin_id:
        return

    msg = (
        f"<b>⚠️ Low Inventory Alert!</b>\n\n"
        f"Product <b>{product.name}</b> is running low on stock.\n"
        f"<b>Remaining quantity:</b> {product.stock_quantity}\n"
        f"Please restock soon!"
    )

    telegram = TelegramService()
    try:
        await telegram.send_message(chat_id=admin_id, text=msg)
    except Exception as exc:
        logger.error("Error in notify_low_stock: %s", exc)
    finally:
        await telegram.close()
