"""
Automated Keyword Responder Service.
Scans incoming customer messages for keywords, queries database for product information,
and formats responses with live pricing and stock levels.
"""

import re
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.auto_response import AutoResponse
from app.models.product import Product


async def find_response(db: AsyncSession, message_text: str) -> Optional[str]:
    """
    Match incoming message text against keywords and products to generate a response.
    
    Args:
        db: Async database session.
        message_text: Raw incoming text from Telegram/Instagram.
        
    Returns:
        Formatted response string, or None if no match is found.
    """
    if not message_text:
        return None

    # 1. Normalize message
    text = message_text.strip().lower()

    # 2. Check if any product name is mentioned in the message
    product_stmt = select(Product).where(Product.is_active == True)
    product_result = await db.execute(product_stmt)
    products = product_result.scalars().all()
    
    matched_product: Optional[Product] = None
    for p in products:
        # Match product name as substring or word
        if p.name.lower() in text:
            matched_product = p
            break

    # 3. Check for specific AutoResponse keywords (exact or word boundary match)
    stmt = select(AutoResponse)
    result = await db.execute(stmt)
    responses = result.scalars().all()
    
    matched_response: Optional[AutoResponse] = None
    for resp in responses:
        kw = resp.keyword.lower()
        # Word boundary or exact match check
        pattern = rf"\b{re.escape(kw)}\b"
        if re.search(pattern, text) or kw == text:
            matched_response = resp
            break

    # 4. Handle product-specific queries
    if matched_product:
        # If the user asks about price
        if any(w in text for w in ["price", "cost", "how much", "rate", "$"]):
            price_template = "The price of {product_name} is ${price}."
            # See if we have a custom 'price' auto-response
            custom_price = next((r for r in responses if r.keyword == "price"), None)
            if custom_price:
                price_template = custom_price.response_text
            return price_template.format(
                product_name=matched_product.name,
                price=f"{matched_product.price:.2f}",
                stock=matched_product.stock_quantity
            )
        
        # If the user asks about stock
        if any(w in text for w in ["stock", "quantity", "left", "available"]):
            stock_template = "We currently have {stock} units of {product_name} in stock."
            custom_stock = next((r for r in responses if r.keyword == "stock"), None)
            if custom_stock:
                stock_template = custom_stock.response_text
            return stock_template.format(
                product_name=matched_product.name,
                price=f"{matched_product.price:.2f}",
                stock=matched_product.stock_quantity
            )

        # General mention of product - reply with details
        general_template = "{product_name} is available for ${price}. (Stock: {stock})"
        custom_info = next((r for r in responses if r.keyword == "product_info"), None)
        if custom_info:
            general_template = custom_info.response_text
        return general_template.format(
            product_name=matched_product.name,
            price=f"{matched_product.price:.2f}",
            stock=matched_product.stock_quantity
        )

    # 5. Handle general keyword match
    if matched_response:
        # If the response template has variables, but no product matched, see if we can use first active product
        resp_text = matched_response.response_text
        if "{" in resp_text and "}" in resp_text:
            if products:
                # Format using the first product
                first_prod = products[0]
                return resp_text.format(
                    product_name=first_prod.name,
                    price=f"{first_prod.price:.2f}",
                    stock=first_prod.stock_quantity
                )
            else:
                # Strip placeholder strings if no products exist
                return re.sub(r"\{.*?\}", "N/A", resp_text)
        return resp_text

    # 6. Fallback response (only if message matches a general enquiry indicator)
    if any(w in text for w in ["hello", "hi", "hey", "shop", "buy", "order"]):
        default_greeting = "Hello! Welcome to our store. Feel free to browse our products in the Mini App or ask about specific item prices or stock levels."
        custom_hello = next((r for r in responses if r.keyword in ["hello", "welcome"]), None)
        if custom_hello:
            return custom_hello.response_text
        return default_greeting

    return None
