# Enterprise Inventory & Order Backend REST API

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0%20Async-red.svg)](https://www.sqlalchemy.org/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-e92063.svg)](https://docs.pydantic.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![Tests](https://img.shields.io/badge/Pytest-29%20Passing-brightgreen.svg)](https://pytest.org/)

Production-grade, high-concurrency Inventory and Order Management backend built with FastAPI, PostgreSQL, SQLAlchemy 2.0 Async ORM, Alembic migrations, and Pydantic V2.

---

## 🏛 System Architecture & Design Philosophy

This service follows strict enterprise separation of concerns, eliminating single-file anti-patterns:

```
[ HTTP Requests ]
        │
        ▼
[ API Routers (app/api/v1/) ]
   - Path operations, query params & request parsing
   - HTTP status code mapping & DTO serialization
        │
        ▼
[ Services (app/services/) ]
   - Business logic, authorization & validation
   - Atomic database transactions & inventory locks
        │
        ▼
[ Repositories (app/repositories/) ]
   - Pure SQLAlchemy 2.0 async queries & pagination
   - Query composition & row-level locking (SELECT ... FOR UPDATE)
        │
        ▼
[ Models (app/models/) ]
   - Mapped ORM classes with CheckConstraints & Enums
        │
        ▼
[ PostgreSQL / SQLite ]
```

### 🔒 Concurrency & Atomic Transaction Strategy
To guarantee that high-traffic flash sales never cause negative inventory or race conditions:
1. **Row-Level Locking (`SELECT ... FOR UPDATE`)**: Before decrementing stock, each product record is locked inside the database transaction.
2. **Deadlock Prevention**: Product IDs in multi-item orders are deterministically sorted before acquiring locks, preventing circular lock deadlocks under high load.
3. **Automatic Rollbacks**: If any product has insufficient stock or an error occurs, the entire transaction rolls back via transaction savepoints (`begin_nested()`), leaving inventory 100% untouched.
4. **Database-Level Check Constraints**: `CheckConstraint("stock_quantity >= 0")` and `CheckConstraint("price > 0")` enforce non-negative stock directly inside the database engine as defense-in-depth.

---

## 📁 Project Directory Structure

```
.
├── alembic/                    # Database migration scripts & async environment
│   ├── versions/
│   │   └── 001_initial_schema.py
│   └── env.py
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py     # Register, login & current user
│   │   │   │   ├── products.py # Product CRUD & filtering
│   │   │   │   ├── orders.py   # Atomic transactional ordering
│   │   │   │   └── health.py   # DB & API health probe
│   │   │   └── router.py       # API v1 aggregated router
│   │   └── deps.py             # Auth & RBAC dependencies
│   ├── core/
│   │   ├── config.py           # Pydantic-settings BaseSettings
│   │   ├── database.py         # Async engine & session factory
│   │   ├── exceptions.py       # Domain exceptions & handlers
│   │   ├── logging.py          # Structured logging & request middleware
│   │   └── security.py         # Bcrypt hashing & JWT token logic
│   ├── models/                 # SQLAlchemy 2.0 Mapped ORM classes
│   │   ├── base.py             # DeclarativeBase & Mixins
│   │   ├── user.py             # User & UserRole enum
│   │   ├── product.py          # Product with check constraints
│   │   └── order.py            # Order & OrderItem models
│   ├── repositories/           # Data access layer
│   │   ├── base_repository.py
│   │   ├── user_repository.py
│   │   ├── product_repository.py
│   │   └── order_repository.py
│   ├── schemas/                # Pydantic v2 DTOs (Request/Response)
│   │   ├── user.py
│   │   ├── product.py
│   │   ├── order.py
│   │   └── health.py
│   ├── services/               # Business logic layer
│   │   ├── auth_service.py
│   │   ├── product_service.py
│   │   └── order_service.py
│   └── main.py                 # FastAPI application factory
├── tests/                      # Automated test suite
│   ├── conftest.py             # In-memory SQLite fixtures & clients
│   ├── test_auth.py            # Registration, login & token tests
│   ├── test_products.py        # Product CRUD, filters & RBAC tests
│   └── test_orders.py          # Atomic ordering, stock rollbacks & health
├── .env.example                # Sample environment configuration
├── .gitignore
├── alembic.ini
├── Dockerfile                  # Production container definition
├── docker-compose.yml          # Multi-container orchestration (App + Postgres)
├── pyproject.toml              # Project metadata & tool configs
├── requirements.txt            # Pinned dependencies
└── README.md
```

---

## 🚀 Getting Started

### Option A: Run via Docker Compose (Recommended)

Start the API and PostgreSQL container with automated migrations:

```bash
# 1. Start PostgreSQL 16 and FastAPI API
docker compose up -d --build

# 2. View streaming logs
docker compose logs -f api
```

The API is immediately available at `http://localhost:8000`.

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc UI**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/api/v1/health`

To stop:
```bash
docker compose down -v
```

---

### Option B: Local Virtual Environment

#### 1. Prerequisites
- Python 3.11+
- PostgreSQL (or use SQLite for standalone testing)

#### 2. Create Virtual Environment & Install Dependencies
```bash
# Create venv
python -m venv .venv

# Activate venv
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 3. Environment Configuration
Copy `.env.example` to `.env` and set your database credentials:
```bash
cp .env.example .env
```

#### 4. Run Database Migrations
```bash
alembic upgrade head
```

#### 5. Launch Development Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🧪 Running the Test Suite

The test suite runs with `pytest`, `pytest-asyncio`, and `aiosqlite` using an isolated in-memory SQLite database. Tests cover positive flows, security barriers, and edge cases:

```bash
# Run all tests with verbose output
pytest -v

# Run specific test modules
pytest tests/test_orders.py -v
pytest tests/test_auth.py -v
pytest tests/test_products.py -v
```

### Test Coverage Highlights:
- **Authentication**: Registration, duplicate email conflict, password length enforcement, login, invalid credentials, JWT expiry.
- **RBAC**: Admin product creation vs customer/unauthenticated access rejection.
- **Products**: Pagination metadata, name search, price filtering, SKU uniqueness.
- **Order Concurrency & Rollback**:
  - Single & multi-product order fulfillment.
  - Stock decremented atomically.
  - Partial stock shortages rolling back the entire multi-item transaction.
  - Customer order isolation (users cannot read other users' orders; Admins can inspect any order).

---

## 📡 API Reference

Base URL prefix: `/api/v1`

### Authentication (`/api/v1/auth`)
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Public | Register user (`Customer` or `Admin`) |
| `POST` | `/api/v1/auth/login` | Public | Login credentials, returns JWT bearer token |
| `GET` | `/api/v1/auth/me` | Authenticated | Retrieve current user profile |

### Products (`/api/v1/products`)
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/v1/products` | Public | Paginated products with name & price filters |
| `POST` | `/api/v1/products` | **Admin Only** | Create a new product with stock and price |
| `GET` | `/api/v1/products/{id}` | Public | Get single product details by ID |
| `PUT` | `/api/v1/products/{id}` | **Admin Only** | Update product attributes |
| `DELETE` | `/api/v1/products/{id}` | **Admin Only** | Remove product by ID |

### Orders (`/api/v1/orders`)
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/api/v1/orders` | Authenticated | Atomically locks & decrements stock to create order |
| `GET` | `/api/v1/orders/{id}` | Authenticated | View order details (Owner or Admin) |
| `GET` | `/api/v1/orders` | Authenticated | Paginated orders (Customer views own; Admin views all) |

### System Health (`/api/v1/health`)
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/v1/health` | Public | Validates API & database connectivity |

---

## 🛡 Uniform Error Format

All error responses across the API follow a deterministic JSON envelope:

```json
{
  "error": "INSUFFICIENT_STOCK",
  "message": "Insufficient stock for product '550e8400-e29b-41d4-a716-446655440000'. Requested: 15, Available: 10",
  "details": {
    "product_id": "550e8400-e29b-41d4-a716-446655440000",
    "requested_quantity": 15,
    "available_quantity": 10
  }
}
```

Common error codes:
- `NOT_FOUND` (404)
- `CONFLICT` (409)
- `INSUFFICIENT_STOCK` (400)
- `AUTHENTICATION_FAILED` (401)
- `PERMISSION_DENIED` (403)
- `VALIDATION_ERROR` (422)
- `INTERNAL_SERVER_ERROR` (500)
