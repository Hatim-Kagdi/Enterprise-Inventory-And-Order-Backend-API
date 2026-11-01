from decimal import Decimal
from typing import Annotated, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import require_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.product import (
    ProductCreate,
    ProductPagination,
    ProductRead,
    ProductUpdate,
)
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Products"])


@router.get(
    "",
    response_model=ProductPagination,
    status_code=status.HTTP_200_OK,
    summary="List products with filters and pagination",
    description="Retrieves a paginated list of products. Can be filtered by name search, price range, and active status.",
)
async def list_products(
    session: Annotated[AsyncSession, Depends(get_db)],
    name: Optional[str] = Query(None, description="Filter by product name substring"),
    min_price: Optional[Decimal] = Query(None, ge=Decimal("0.00"), description="Minimum price filter"),
    max_price: Optional[Decimal] = Query(None, ge=Decimal("0.00"), description="Maximum price filter"),
    is_active: Optional[bool] = Query(None, description="Filter active/inactive products"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
) -> ProductPagination:
    service = ProductService(session)
    return await service.list_products(
        name=name,
        min_price=min_price,
        max_price=max_price,
        is_active=is_active,
        page=page,
        limit=limit,
    )


@router.post(
    "",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product (Admin only)",
    description="Creates a new inventory product. Restricted to users with the Administrator role.",
)
async def create_product(
    product_in: ProductCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> ProductRead:
    service = ProductService(session)
    product = await service.create_product(product_in)
    return ProductRead.model_validate(product)


@router.get(
    "/{product_id}",
    response_model=ProductRead,
    status_code=status.HTTP_200_OK,
    summary="Get product details",
    description="Retrieves single product details by product ID.",
)
async def get_product(
    product_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProductRead:
    service = ProductService(session)
    product = await service.get_product_by_id(product_id)
    return ProductRead.model_validate(product)


@router.put(
    "/{product_id}",
    response_model=ProductRead,
    status_code=status.HTTP_200_OK,
    summary="Update product (Admin only)",
    description="Updates existing product details. Restricted to Administrator role.",
)
async def update_product(
    product_id: UUID,
    product_in: ProductUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> ProductRead:
    service = ProductService(session)
    product = await service.update_product(product_id, product_in)
    return ProductRead.model_validate(product)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete product (Admin only)",
    description="Deletes a product by ID. Restricted to Administrator role.",
)
async def delete_product(
    product_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> None:
    service = ProductService(session)
    await service.delete_product(product_id)
