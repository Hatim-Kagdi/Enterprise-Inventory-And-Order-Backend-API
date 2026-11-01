import os
from decimal import Decimal
from typing import AsyncGenerator
import pytest

# Inject test-scoped secret key for isolated test execution
os.environ.setdefault(
    "SECRET_KEY",
    "insecure-test-secret-key-for-pytest-execution-only-32-chars-minimum",
)
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.base import Base
from app.models.product import Product
from app.models.user import User, UserRole

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest.fixture(autouse=True)
async def init_db() -> AsyncGenerator[None, None]:
    """Creates all database tables before each test and tears them down after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yields a test database session."""
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Yields an HTTPX AsyncClient configured with overridden DB dependency."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Creates and persists an Administrator user in the test database."""
    from app.core.security import get_password_hash
    admin = User(
        email="admin@example.com",
        hashed_password=get_password_hash("AdminPass123!"),
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
def admin_headers(admin_user: User) -> dict[str, str]:
    """Returns Authorization bearer headers for Admin user."""
    token = create_access_token(subject=str(admin_user.id), role=admin_user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def customer_user(db_session: AsyncSession) -> User:
    """Creates and persists a Customer user in the test database."""
    from app.core.security import get_password_hash
    customer = User(
        email="customer@example.com",
        hashed_password=get_password_hash("CustomerPass123!"),
        role=UserRole.CUSTOMER,
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    return customer


@pytest.fixture
def customer_headers(customer_user: User) -> dict[str, str]:
    """Returns Authorization bearer headers for Customer user."""
    token = create_access_token(subject=str(customer_user.id), role=customer_user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def sample_product(db_session: AsyncSession) -> Product:
    """Creates and persists a sample product with 10 units in stock."""
    product = Product(
        name="Enterprise Laptop",
        sku="LAPTOP-ENT-001",
        description="High-performance developer workstation",
        price=Decimal("1299.99"),
        stock_quantity=10,
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product
