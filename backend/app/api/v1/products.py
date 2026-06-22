"""
Products API endpoints.
"""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.api.deps import get_db, require_admin, get_current_user_optional
from app.config import get_settings, Settings
from app.models.product import Product
from app.models.seller import Seller
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, ProductList
from app.services import storage

router = APIRouter()


async def get_or_create_default_seller(db: AsyncSession, settings: Settings) -> Seller:
    """Helper to get the main admin seller or create it if not exists."""
    stmt = select(Seller).where(Seller.telegram_id == settings.ADMIN_TELEGRAM_ID)
    result = await db.execute(stmt)
    seller = result.scalar_one_or_none()
    if not seller:
        seller = Seller(
            telegram_id=settings.ADMIN_TELEGRAM_ID,
            store_name="My OmniShop",
        )
        db.add(seller)
        await db.commit()
        await db.refresh(seller)
    return seller


@router.get("", response_model=ProductList)
async def list_products(
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    List active products.
    If authorized as admin and include_inactive is true, returns inactive products too.
    """
    # Check if admin is requesting inactive products
    is_admin = current_user is not None and current_user.get("role") == "admin"
    should_include_inactive = include_inactive and is_admin

    query = select(Product)
    
    if not should_include_inactive:
        query = query.where(Product.is_active == True)

    if search:
        query = query.where(
            or_(
                Product.name.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%"),
            )
        )

    # Count query
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Execute main query
    query = query.order_by(Product.name).offset(offset).limit(limit)
    result = await db.execute(query)
    products = result.scalars().all()

    return ProductList(items=products, total=total)


@router.post("/upload-image", status_code=status.HTTP_201_CREATED)
async def upload_product_image(
    request: Request,
    file: UploadFile = File(...),
    admin_user: dict = Depends(require_admin),
):
    """
    Upload a product photo (Admin only) and return its public URL.

    The returned ``url`` is what the client should send back as ``image_url``
    when creating or updating a product. Images are stored on Cloudinary in
    production, or on the local disk during development.
    """
    if file.content_type not in storage.ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image type. Please upload a JPEG, PNG, WebP, or GIF.",
        )

    data = await file.read()

    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    if len(data) > storage.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image is too large (max {get_settings().MAX_UPLOAD_SIZE_MB} MB).",
        )

    try:
        url = await run_in_threadpool(
            storage.save_image, data, file.content_type, str(request.base_url)
        )
    except Exception as exc:  # noqa: BLE001 - surface a clean error to the client
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Image upload failed. Please try again.",
        ) from exc

    return {"url": url}


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get details of a single product by UUID."""
    stmt = select(Product).where(Product.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: dict = Depends(require_admin),
    settings: Settings = Depends(get_settings),
):
    """Create a new product (Admin only)."""
    seller = await get_or_create_default_seller(db, settings)
    
    product = Product(
        seller_id=seller.id,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        stock_quantity=payload.stock_quantity,
        image_url=payload.image_url,
        is_active=True,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: dict = Depends(require_admin),
):
    """Update a product (Admin only)."""
    stmt = select(Product).where(Product.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Apply updates
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: dict = Depends(require_admin),
):
    """Soft-delete a product by setting is_active=False (Admin only)."""
    stmt = select(Product).where(Product.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    product.is_active = False
    await db.commit()
    return None
