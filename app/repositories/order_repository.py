from typing import Optional, Sequence, Tuple
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.order import Order, OrderItem
from app.repositories.base_repository import BaseRepository


class OrderRepository(BaseRepository[Order]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Order, session)

    async def get_by_id_with_items(self, order_id: UUID) -> Optional[Order]:
        """Fetches an order with eagerly loaded items and associated products."""
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.user),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_user(
        self,
        user_id: UUID,
        offset: int = 0,
        limit: int = 20,
    ) -> Tuple[Sequence[Order], int]:
        """Lists orders for a specific user with pagination."""
        base_stmt = (
            select(Order)
            .where(Order.user_id == user_id)
            .options(
                selectinload(Order.items).selectinload(OrderItem.product),
            )
        )
        count_stmt = select(func.count(Order.id)).where(Order.user_id == user_id)

        total_result = await self.session.execute(count_stmt)
        total_count = total_result.scalar() or 0

        paginated_stmt = base_stmt.order_by(Order.created_at.desc()).offset(offset).limit(limit)
        items_result = await self.session.execute(paginated_stmt)
        items = items_result.scalars().all()

        return items, total_count

    async def list_all_orders(
        self,
        offset: int = 0,
        limit: int = 20,
    ) -> Tuple[Sequence[Order], int]:
        """Lists all orders in the system (Admin only) with pagination."""
        base_stmt = select(Order).options(
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.user),
        )
        count_stmt = select(func.count(Order.id))

        total_result = await self.session.execute(count_stmt)
        total_count = total_result.scalar() or 0

        paginated_stmt = base_stmt.order_by(Order.created_at.desc()).offset(offset).limit(limit)
        items_result = await self.session.execute(paginated_stmt)
        items = items_result.scalars().all()

        return items, total_count
