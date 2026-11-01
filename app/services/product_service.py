import math
from decimal import Decimal
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import ConflictException, EntityNotFoundException
from app.models.product import Product
from app.repositories.product_repository import ProductRepository
from app.schemas.product import (
    ProductCreate,
    ProductPagination,
    ProductRead,
    ProductUpdate,
)


class ProductService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.product_repo = ProductRepository(session)

    async def create_product(self, product_in: ProductCreate) -> Product:
        """Creates a new product ensuring unique SKU."""
        normalized_sku = product_in.sku.upper().strip()
        existing = await self.product_repo.get_by_sku(normalized_sku)
        if existing:
            raise ConflictException(
                message=f"Product with SKU '{normalized_sku}' already exists",
                details={"sku": normalized_sku},
            )

        product = Product(
            name=product_in.name.strip(),
            sku=normalized_sku,
            description=product_in.description,
            price=product_in.price,
            stock_quantity=product_in.stock_quantity,
            is_active=product_in.is_active,
        )

        created_product = await self.product_repo.create(product)
        await self.session.commit()
        await self.session.refresh(created_product)
        return created_product

    async def get_product_by_id(self, product_id: UUID) -> Product:
        """Retrieves a product by ID or raises 404."""
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            raise EntityNotFoundException("Product", product_id)
        return product

    async def list_products(
        self,
        name: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        limit: int = 20,
    ) -> ProductPagination:
        """Lists products with optional filtering and pagination metadata."""
        if page < 1:
            page = 1
        if limit < 1:
            limit = 20
        elif limit > 100:
            limit = 100

        offset = (page - 1) * limit
        items, total = await self.product_repo.list_filtered(
            name=name,
            min_price=min_price,
            max_price=max_price,
            is_active=is_active,
            offset=offset,
            limit=limit,
        )

        total_pages = math.ceil(total / limit) if total > 0 else 0
        product_reads = [ProductRead.model_validate(p) for p in items]

        return ProductPagination(
            items=product_reads,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
        )

    async def update_product(self, product_id: UUID, product_in: ProductUpdate) -> Product:
        """Updates product attributes with conflict checks."""
        product = await self.get_product_by_id(product_id)

        update_data = product_in.model_dump(exclude_unset=True)
        if "sku" in update_data and update_data["sku"]:
            normalized_sku = update_data["sku"].upper().strip()
            if normalized_sku != product.sku:
                existing = await self.product_repo.get_by_sku(normalized_sku)
                if existing and existing.id != product.id:
                    raise ConflictException(
                        message=f"Product with SKU '{normalized_sku}' already exists",
                        details={"sku": normalized_sku},
                    )
            update_data["sku"] = normalized_sku

        for field, value in update_data.items():
            setattr(product, field, value)

        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def delete_product(self, product_id: UUID) -> None:
        """Deletes a product by ID."""
        product = await self.get_product_by_id(product_id)
        await self.product_repo.delete(product)
        await self.session.commit()
