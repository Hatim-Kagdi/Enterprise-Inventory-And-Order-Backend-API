from collections import defaultdict
from decimal import Decimal
import math
from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import (
    BadRequestException,
    EntityNotFoundException,
    InsufficientStockException,
    PermissionDeniedException,
)
from app.models.order import Order, OrderItem, OrderStatus
from app.models.user import User, UserRole
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.order import (
    OrderCreate,
    OrderItemRead,
    OrderPagination,
    OrderRead,
)


class OrderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.order_repo = OrderRepository(session)
        self.product_repo = ProductRepository(session)

    async def create_order(self, user_id: UUID, order_in: OrderCreate) -> Order:
        """Atomically creates an order, validates stock, decrements inventory with row-level locks,

        and automatically rolls back on any violation.
        """
        if not order_in.items:
            raise BadRequestException("Order must contain at least one item")

        # 1. Aggregate quantities per product to handle duplicate items cleanly
        aggregated_quantities: dict[UUID, int] = defaultdict(int)
        for item in order_in.items:
            if item.quantity <= 0:
                raise BadRequestException(f"Quantity for product {item.product_id} must be greater than zero")
            aggregated_quantities[item.product_id] += item.quantity

        # 2. Sort product IDs to prevent database deadlocks under high concurrent ordering
        sorted_product_ids = sorted(aggregated_quantities.keys())

        # 3. Execute in an atomic transaction block
        created_order_id: UUID | None = None
        try:
            tx = self.session.begin_nested() if self.session.in_transaction() else self.session.begin()
            async with tx:
                total_amount = Decimal("0.00")
                order_items: List[OrderItem] = []

                for prod_id in sorted_product_ids:
                    # Acquire row-level lock on the product record
                    product = await self.product_repo.get_by_id_for_update(prod_id)
                    if not product:
                        raise EntityNotFoundException("Product", prod_id)

                    if not product.is_active:
                        raise BadRequestException(
                            f"Product '{product.name}' (SKU: {product.sku}) is inactive and cannot be ordered"
                        )

                    requested_qty = aggregated_quantities[prod_id]

                    # Check inventory constraint
                    if product.stock_quantity < requested_qty:
                        raise InsufficientStockException(
                            product_id=str(prod_id),
                            requested_quantity=requested_qty,
                            available_quantity=product.stock_quantity,
                        )

                    # Atomically decrement inventory
                    product.stock_quantity -= requested_qty

                    # Calculate item total
                    unit_price = product.price
                    line_total = unit_price * requested_qty
                    total_amount += line_total

                    order_item = OrderItem(
                        product_id=prod_id,
                        quantity=requested_qty,
                        unit_price=unit_price,
                    )
                    order_items.append(order_item)

                # Create order with associated items
                order = Order(
                    user_id=user_id,
                    total_amount=total_amount,
                    status=OrderStatus.PENDING,
                    items=order_items,
                )
                self.session.add(order)
                await self.session.flush()
                created_order_id = order.id

            if self.session.in_transaction():
                await self.session.commit()
        except Exception:
            if self.session.in_transaction():
                await self.session.rollback()
            raise

        # 4. Return the fully loaded order record with relations
        assert created_order_id is not None
        refreshed_order = await self.order_repo.get_by_id_with_items(created_order_id)
        if not refreshed_order:
            raise EntityNotFoundException("Order", created_order_id)
        return refreshed_order

    async def get_order_by_id(self, order_id: UUID, current_user: User) -> Order:
        """Retrieves order with RBAC authorization check (Admins see any, Customers see own)."""
        order = await self.order_repo.get_by_id_with_items(order_id)
        if not order:
            raise EntityNotFoundException("Order", order_id)

        if current_user.role != UserRole.ADMIN and order.user_id != current_user.id:
            raise PermissionDeniedException(
                "You do not have permission to view this order"
            )

        return order

    async def list_orders(
        self,
        current_user: User,
        page: int = 1,
        limit: int = 20,
    ) -> OrderPagination:
        """Lists orders with pagination. Admin gets all orders; Customer gets their own."""
        if page < 1:
            page = 1
        if limit < 1:
            limit = 20
        elif limit > 100:
            limit = 100

        offset = (page - 1) * limit

        if current_user.role == UserRole.ADMIN:
            items, total = await self.order_repo.list_all_orders(offset=offset, limit=limit)
        else:
            items, total = await self.order_repo.list_by_user(
                user_id=current_user.id,
                offset=offset,
                limit=limit,
            )

        total_pages = math.ceil(total / limit) if total > 0 else 0

        order_reads: List[OrderRead] = []
        for o in items:
            item_reads = [
                OrderItemRead(
                    id=it.id,
                    product_id=it.product_id,
                    quantity=it.quantity,
                    unit_price=it.unit_price,
                    product_name=it.product.name if it.product else None,
                )
                for it in o.items
            ]
            order_reads.append(
                OrderRead(
                    id=o.id,
                    user_id=o.user_id,
                    total_amount=o.total_amount,
                    status=o.status,
                    created_at=o.created_at,
                    items=item_reads,
                )
            )

        return OrderPagination(
            items=order_reads,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
        )
