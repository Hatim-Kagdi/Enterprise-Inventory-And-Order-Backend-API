from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import create_access_token, get_password_hash
from app.models.product import Product
from app.models.user import User, UserRole


@pytest.mark.asyncio
async def test_create_order_success(
    client: AsyncClient,
    customer_headers: dict[str, str],
    sample_product: Product,
    db_session: AsyncSession,
) -> None:
    # Initial stock is 10
    assert sample_product.stock_quantity == 10

    order_payload = {
        "items": [
            {
                "product_id": str(sample_product.id),
                "quantity": 2,
            }
        ]
    }

    response = await client.post("/api/v1/orders", json=order_payload, headers=customer_headers)
    assert response.status_code == 201
    order_data = response.json()
    assert order_data["status"] == "PENDING"
    assert Decimal(order_data["total_amount"]) == Decimal("1299.99") * 2
    assert len(order_data["items"]) == 1
    assert order_data["items"][0]["quantity"] == 2
    assert Decimal(order_data["items"][0]["unit_price"]) == Decimal("1299.99")

    # Verify inventory was decremented in database
    await db_session.refresh(sample_product)
    assert sample_product.stock_quantity == 8


@pytest.mark.asyncio
async def test_create_order_insufficient_stock_rollback(
    client: AsyncClient,
    customer_headers: dict[str, str],
    sample_product: Product,
    db_session: AsyncSession,
) -> None:
    # Stock is 10, requesting 15 units
    order_payload = {
        "items": [
            {
                "product_id": str(sample_product.id),
                "quantity": 15,
            }
        ]
    }

    response = await client.post("/api/v1/orders", json=order_payload, headers=customer_headers)
    assert response.status_code == 400
    err = response.json()
    assert err["error"] == "INSUFFICIENT_STOCK"
    assert "Insufficient stock" in err["message"]

    # Verify stock remained untouched (rolled back to 10)
    await db_session.refresh(sample_product)
    assert sample_product.stock_quantity == 10


@pytest.mark.asyncio
async def test_create_order_inactive_product(
    client: AsyncClient,
    customer_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    inactive_product = Product(
        name="Discontinued Item",
        sku="DISC-001",
        price=Decimal("50.00"),
        stock_quantity=100,
        is_active=False,
    )
    db_session.add(inactive_product)
    await db_session.commit()
    await db_session.refresh(inactive_product)

    order_payload = {
        "items": [{"product_id": str(inactive_product.id), "quantity": 1}]
    }

    response = await client.post("/api/v1/orders", json=order_payload, headers=customer_headers)
    assert response.status_code == 400
    assert "inactive" in response.json()["message"].lower()


@pytest.mark.asyncio
async def test_create_order_nonexistent_product(
    client: AsyncClient,
    customer_headers: dict[str, str],
) -> None:
    order_payload = {
        "items": [{"product_id": str(uuid.uuid4()), "quantity": 1}]
    }
    response = await client.post("/api/v1/orders", json=order_payload, headers=customer_headers)
    assert response.status_code == 404
    assert response.json()["error"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_get_order_rbac_protection(
    client: AsyncClient,
    customer_headers: dict[str, str],
    admin_headers: dict[str, str],
    sample_product: Product,
    db_session: AsyncSession,
) -> None:
    # 1. Customer A places an order
    res = await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": str(sample_product.id), "quantity": 1}]},
        headers=customer_headers,
    )
    assert res.status_code == 201
    order_id = res.json()["id"]

    # 2. Customer A can view their order
    res_cust_a = await client.get(f"/api/v1/orders/{order_id}", headers=customer_headers)
    assert res_cust_a.status_code == 200
    assert res_cust_a.json()["id"] == order_id

    # 3. Customer B attempts to view Customer A's order -> 403 Forbidden
    other_customer = User(
        email="other@example.com",
        hashed_password=get_password_hash("Password123!"),
        role=UserRole.CUSTOMER,
    )
    db_session.add(other_customer)
    await db_session.commit()
    await db_session.refresh(other_customer)
    other_token = create_access_token(subject=str(other_customer.id), role=other_customer.role.value)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    res_cust_b = await client.get(f"/api/v1/orders/{order_id}", headers=other_headers)
    assert res_cust_b.status_code == 403
    assert res_cust_b.json()["error"] == "PERMISSION_DENIED"

    # 4. Admin can view Customer A's order -> 200 OK
    res_admin = await client.get(f"/api/v1/orders/{order_id}", headers=admin_headers)
    assert res_admin.status_code == 200
    assert res_admin.json()["id"] == order_id


@pytest.mark.asyncio
async def test_list_orders(
    client: AsyncClient,
    customer_headers: dict[str, str],
    sample_product: Product,
) -> None:
    # Place an order first
    await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": str(sample_product.id), "quantity": 1}]},
        headers=customer_headers,
    )

    response = await client.get("/api/v1/orders", headers=customer_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_health_check_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_create_order_multiple_products_success(
    client: AsyncClient,
    customer_headers: dict[str, str],
    sample_product: Product,
    db_session: AsyncSession,
) -> None:
    # Create second product
    product2 = Product(
        name="Mechanical Mouse",
        sku="MOUSE-001",
        price=Decimal("49.99"),
        stock_quantity=20,
        is_active=True,
    )
    db_session.add(product2)
    await db_session.commit()
    await db_session.refresh(product2)

    order_payload = {
        "items": [
            {"product_id": str(sample_product.id), "quantity": 3},
            {"product_id": str(product2.id), "quantity": 5},
        ]
    }

    response = await client.post("/api/v1/orders", json=order_payload, headers=customer_headers)
    assert response.status_code == 201
    data = response.json()
    expected_total = (Decimal("1299.99") * 3) + (Decimal("49.99") * 5)
    assert Decimal(data["total_amount"]) == expected_total
    assert len(data["items"]) == 2

    # Verify both inventory stocks were decremented
    await db_session.refresh(sample_product)
    await db_session.refresh(product2)
    assert sample_product.stock_quantity == 7  # 10 - 3
    assert product2.stock_quantity == 15      # 20 - 5


@pytest.mark.asyncio
async def test_create_order_partial_insufficient_stock_rolls_back_all(
    client: AsyncClient,
    customer_headers: dict[str, str],
    sample_product: Product,
    db_session: AsyncSession,
) -> None:
    # Product 1 has 10 stock. Product 2 has 2 stock.
    product2 = Product(
        name="Limited Edition Pad",
        sku="PAD-LTD-001",
        price=Decimal("25.00"),
        stock_quantity=2,
        is_active=True,
    )
    db_session.add(product2)
    await db_session.commit()
    await db_session.refresh(product2)

    # Order asks for 3 of product 1 (valid) and 5 of product 2 (exceeds stock of 2!)
    order_payload = {
        "items": [
            {"product_id": str(sample_product.id), "quantity": 3},
            {"product_id": str(product2.id), "quantity": 5},
        ]
    }

    response = await client.post("/api/v1/orders", json=order_payload, headers=customer_headers)
    assert response.status_code == 400
    assert response.json()["error"] == "INSUFFICIENT_STOCK"

    # Verify BOTH products were untouched due to transaction rollback
    await db_session.refresh(sample_product)
    await db_session.refresh(product2)
    assert sample_product.stock_quantity == 10
    assert product2.stock_quantity == 2


@pytest.mark.asyncio
async def test_create_order_duplicate_items_aggregated(
    client: AsyncClient,
    customer_headers: dict[str, str],
    sample_product: Product,
    db_session: AsyncSession,
) -> None:
    # Client sends same product twice: qty 2 and qty 3 -> aggregated to 5
    order_payload = {
        "items": [
            {"product_id": str(sample_product.id), "quantity": 2},
            {"product_id": str(sample_product.id), "quantity": 3},
        ]
    }

    response = await client.post("/api/v1/orders", json=order_payload, headers=customer_headers)
    assert response.status_code == 201
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 5
    assert Decimal(data["total_amount"]) == Decimal("1299.99") * 5

    await db_session.refresh(sample_product)
    assert sample_product.stock_quantity == 5


@pytest.mark.asyncio
async def test_create_order_zero_quantity_rejected(
    client: AsyncClient,
    customer_headers: dict[str, str],
    sample_product: Product,
) -> None:
    order_payload = {
        "items": [{"product_id": str(sample_product.id), "quantity": 0}]
    }
    response = await client.post("/api/v1/orders", json=order_payload, headers=customer_headers)
    assert response.status_code == 422

