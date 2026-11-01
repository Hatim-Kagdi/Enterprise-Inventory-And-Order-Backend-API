from decimal import Decimal
from typing import Optional, Sequence, Tuple
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.product import Product
from app.repositories.base_repository import BaseRepository


class ProductRepository(BaseRepository[Product]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Product, session)

    async def get_by_sku(self, sku: str) -> Optional[Product]:
        stmt = select(Product).where(Product.sku == sku.upper().strip())
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_id_for_update(self, product_id: UUID) -> Optional[Product]:
        """Fetches product with row-level lock (SELECT FOR UPDATE) to ensure concurrency safety."""
        stmt = select(Product).where(Product.id == product_id).with_for_update()
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_filtered(
        self,
        name: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        is_active: Optional[bool] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Tuple[Sequence[Product], int]:
        """Lists products with optional filtering and returns (items, total_count)."""
        base_stmt = select(Product)
        count_stmt = select(func.count(Product.id))

        filters = []
        if name:
            filters.append(Product.name.ilike(f"%{name}%"))
        if min_price is not None:
            filters.append(Product.price >= min_price)
        if max_price is not None:
            filters.append(Product.price <= max_price)
        if is_active is not None:
            filters.append(Product.is_active == is_active)

        if filters:
            base_stmt = base_stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)

        total_result = await self.session.execute(count_stmt)
        total_count = total_result.scalar() or 0

        paginated_stmt = base_stmt.order_by(Product.created_at.desc()).offset(offset).limit(limit)
        items_result = await self.session.execute(paginated_stmt)
        items = items_result.scalars().all()

        return items, total_count
