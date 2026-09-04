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


@pytest.mark.asyncio
async def test_product_category_filtering(client: AsyncClient, mock_admin_token: str):
    """Test product creation with category and filtering by category."""
    headers = {"Authorization": f"Bearer {mock_admin_token}"}
    
    # Create product in Electronics
    res1 = await client.post(
        "/api/v1/products",
        json={"name": "Smartphone", "price": 499.0, "category": "Electronics"},
        headers=headers,
    )
    assert res1.status_code == 201
    assert res1.json()["category"] == "Electronics"

    # Create product in Clothing
    res2 = await client.post(
        "/api/v1/products",
        json={"name": "T-Shirt", "price": 19.0, "category": "Clothing"},
        headers=headers,
    )
    assert res2.status_code == 201
    assert res2.json()["category"] == "Clothing"

    # Filter by Electronics
    res_elec = await client.get("/api/v1/products?category=Electronics")
    assert res_elec.status_code == 200
    names = [p["name"] for p in res_elec.json()["items"]]
    assert "Smartphone" in names
    assert "T-Shirt" not in names

    # Filter by Clothing
    res_cloth = await client.get("/api/v1/products?category=Clothing")
    assert res_cloth.status_code == 200
    names = [p["name"] for p in res_cloth.json()["items"]]
    assert "T-Shirt" in names
    assert "Smartphone" not in names


@pytest.mark.asyncio
async def test_product_soft_delete_and_restore(client: AsyncClient, mock_admin_token: str):
    """Test soft deleting a product and restoring it via PATCH /restore."""
    headers = {"Authorization": f"Bearer {mock_admin_token}"}

    # Create product
    res = await client.post(
        "/api/v1/products",
        json={"name": "Deletable Item", "price": 15.0},
        headers=headers,
    )
    assert res.status_code == 201
    product_id = res.json()["id"]

    # Delete product (soft-delete)
    del_res = await client.delete(f"/api/v1/products/{product_id}", headers=headers)
    assert del_res.status_code in (200, 204)

    # Inactive product should not be in default list
    list_res = await client.get("/api/v1/products")
    ids = [p["id"] for p in list_res.json()["items"]]
    assert product_id not in ids

    # Inactive product should be visible with include_inactive=true
    list_all = await client.get("/api/v1/products?include_inactive=true", headers=headers)
    assert any(p["id"] == product_id and p["is_active"] is False for p in list_all.json()["items"])

    # Restore product
    restore_res = await client.patch(f"/api/v1/products/{product_id}/restore", headers=headers)
    assert restore_res.status_code == 200
    assert restore_res.json()["is_active"] is True

    # Now visible in active list again
    list_active = await client.get("/api/v1/products")
    ids_active = [p["id"] for p in list_active.json()["items"]]
    assert product_id in ids_active

