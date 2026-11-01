from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from app.models.product import Product


@pytest.mark.asyncio
async def test_admin_create_product_success(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    payload = {
        "name": "Wireless Mechanical Keyboard",
        "sku": "KB-WL-001",
        "description": "Custom switch mechanical keyboard",
        "price": "149.99",
        "stock_quantity": 50,
        "is_active": True,
    }
    response = await client.post("/api/v1/products", json=payload, headers=admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Wireless Mechanical Keyboard"
    assert data["sku"] == "KB-WL-001"
    assert Decimal(data["price"]) == Decimal("149.99")
    assert data["stock_quantity"] == 50
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_customer_cannot_create_product(
    client: AsyncClient,
    customer_headers: dict[str, str],
) -> None:
    payload = {
        "name": "Unauthorized Product",
        "sku": "UNAUTH-001",
        "price": "10.00",
        "stock_quantity": 5,
    }
    response = await client.post("/api/v1/products", json=payload, headers=customer_headers)
    assert response.status_code == 403
    assert response.json()["error"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_unauthenticated_cannot_create_product(client: AsyncClient) -> None:
    payload = {
        "name": "No Auth Product",
        "sku": "NOAUTH-001",
        "price": "10.00",
        "stock_quantity": 5,
    }
    response = await client.post("/api/v1/products", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_duplicate_sku_conflict(
    client: AsyncClient,
    admin_headers: dict[str, str],
    sample_product: Product,
) -> None:
    payload = {
        "name": "Another Laptop",
        "sku": sample_product.sku,  # Duplicate SKU
        "price": "999.00",
        "stock_quantity": 5,
    }
    response = await client.post("/api/v1/products", json=payload, headers=admin_headers)
    assert response.status_code == 409
    assert response.json()["error"] == "CONFLICT"


@pytest.mark.asyncio
async def test_invalid_product_payload(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    # Negative price
    payload = {
        "name": "Negative Price",
        "sku": "NEG-PRICE-001",
        "price": "-10.00",
        "stock_quantity": 5,
    }
    response = await client.post("/api/v1/products", json=payload, headers=admin_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_products_and_filter(
    client: AsyncClient,
    sample_product: Product,
) -> None:
    response = await client.get("/api/v1/products")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    assert data["page"] == 1
    assert data["items"][0]["sku"] == sample_product.sku

    # Filter by name
    res_filtered = await client.get("/api/v1/products?name=Laptop")
    assert res_filtered.status_code == 200
    assert len(res_filtered.json()["items"]) >= 1

    # Filter with non-matching price range
    res_empty = await client.get("/api/v1/products?min_price=5000.00")
    assert res_empty.status_code == 200
    assert res_empty.json()["total"] == 0


@pytest.mark.asyncio
async def test_get_product_by_id(
    client: AsyncClient,
    sample_product: Product,
) -> None:
    response = await client.get(f"/api/v1/products/{sample_product.id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(sample_product.id)


@pytest.mark.asyncio
async def test_get_product_not_found(client: AsyncClient) -> None:
    fake_id = uuid.uuid4()
    response = await client.get(f"/api/v1/products/{fake_id}")
    assert response.status_code == 404
    assert response.json()["error"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_admin_update_product(
    client: AsyncClient,
    admin_headers: dict[str, str],
    sample_product: Product,
) -> None:
    payload = {
        "price": "1199.50",
        "stock_quantity": 25,
    }
    response = await client.put(
        f"/api/v1/products/{sample_product.id}",
        json=payload,
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert Decimal(data["price"]) == Decimal("1199.50")
    assert data["stock_quantity"] == 25


@pytest.mark.asyncio
async def test_admin_delete_product(
    client: AsyncClient,
    admin_headers: dict[str, str],
    sample_product: Product,
) -> None:
    response = await client.delete(
        f"/api/v1/products/{sample_product.id}",
        headers=admin_headers,
    )
    assert response.status_code == 204

    # Verify deleted
    get_res = await client.get(f"/api/v1/products/{sample_product.id}")
    assert get_res.status_code == 404
