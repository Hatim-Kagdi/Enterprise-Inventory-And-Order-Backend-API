import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient) -> None:
    payload = {
        "email": "newuser@example.com",
        "password": "SecurePassword123!",
        "role": "Customer",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["role"] == "Customer"
    assert "id" in data
    assert "created_at" in data
    assert "password" not in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient) -> None:
    payload = {
        "email": "duplicate@example.com",
        "password": "SecurePassword123!",
        "role": "Customer",
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    error_data = res2.json()
    assert error_data["error"] == "CONFLICT"
    assert "already exists" in error_data["message"]


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient) -> None:
    payload = {
        "email": "shortpass@example.com",
        "password": "short",
        "role": "Customer",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    assert response.json()["error"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    # 1. Register user
    reg_payload = {
        "email": "loginuser@example.com",
        "password": "ValidPassword123!",
        "role": "Customer",
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    # 2. Login
    login_payload = {
        "email": "loginuser@example.com",
        "password": "ValidPassword123!",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 20


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient) -> None:
    reg_payload = {
        "email": "wrongpass@example.com",
        "password": "ValidPassword123!",
        "role": "Customer",
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {
        "email": "wrongpass@example.com",
        "password": "WrongPassword!",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    assert response.json()["error"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient) -> None:
    login_payload = {
        "email": "nonexistent@example.com",
        "password": "SomePassword123!",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    assert response.json()["error"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_get_current_user_me(client: AsyncClient, customer_headers: dict[str, str]) -> None:
    response = await client.get("/api/v1/auth/me", headers=customer_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "customer@example.com"
    assert data["role"] == "Customer"


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(client: AsyncClient) -> None:
    headers = {"Authorization": "Bearer invalid.jwt.token"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["error"] == "AUTHENTICATION_FAILED"
