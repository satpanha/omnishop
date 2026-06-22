"""
Product API CRUD tests.
"""

import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_list_products_empty(client: AsyncClient):
    """Test listing products returns an empty collection initially."""
    response = await client.get("/api/v1/products")
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


@pytest.mark.asyncio
async def test_create_product_as_admin(client: AsyncClient, mock_admin_token: str):
    """Test that admins can create new products successfully."""
    headers = {"Authorization": f"Bearer {mock_admin_token}"}
    payload = {
        "name": "Test Product",
        "description": "High quality testing unit",
        "price": 29.99,
        "stock_quantity": 100,
        "image_url": "http://example.com/image.png",
    }
    
    response = await client.post("/api/v1/products", json=payload, headers=headers)
    assert response.status_code == 201
    
    data = response.json()
    assert data["name"] == "Test Product"
    assert data["price"] == "29.99"
    assert data["stock_quantity"] == 100
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_create_product_unauthorized(client: AsyncClient, mock_buyer_token: str):
    """Test that buyers or anonymous users cannot create products."""
    payload = {
        "name": "Test Product",
        "price": 29.99,
    }
    
    # 1. Anonymous request
    response = await client.post("/api/v1/products", json=payload)
    assert response.status_code == 401

    # 2. Buyer request (not admin)
    headers = {"Authorization": f"Bearer {mock_buyer_token}"}
    response = await client.post("/api/v1/products", json=payload, headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_product_not_found(client: AsyncClient):
    """Test retrieving non-existent product UUID returns 404."""
    random_uuid = str(uuid.uuid4())
    response = await client.get(f"/api/v1/products/{random_uuid}")
    assert response.status_code == 404
