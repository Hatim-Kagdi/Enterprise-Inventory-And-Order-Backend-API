from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.order import (
    OrderCreate,
    OrderItemRead,
    OrderPagination,
    OrderRead,
)
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an order",
    description=(
        "Places an order containing one or more items. "
        "Atomically locks inventory, checks availability, and decrements stock. "
        "Rolls back transaction completely if any item has insufficient stock."
    ),
)
async def create_order(
    order_in: OrderCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OrderRead:
    service = OrderService(session)
    order = await service.create_order(user_id=current_user.id, order_in=order_in)

    item_reads = [
        OrderItemRead(
            id=it.id,
            product_id=it.product_id,
            quantity=it.quantity,
            unit_price=it.unit_price,
            product_name=it.product.name if it.product else None,
        )
        for it in order.items
    ]

    return OrderRead(
        id=order.id,
        user_id=order.user_id,
        total_amount=order.total_amount,
        status=order.status,
        created_at=order.created_at,
        items=item_reads,
    )


@router.get(
    "/{order_id}",
    response_model=OrderRead,
    status_code=status.HTTP_200_OK,
    summary="Get order details",
    description="Retrieves order details by ID. Customers can only view their own orders; Admins can view any order.",
)
async def get_order(
    order_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OrderRead:
    service = OrderService(session)
    order = await service.get_order_by_id(order_id=order_id, current_user=current_user)

    item_reads = [
        OrderItemRead(
            id=it.id,
            product_id=it.product_id,
            quantity=it.quantity,
            unit_price=it.unit_price,
            product_name=it.product.name if it.product else None,
        )
        for it in order.items
    ]

    return OrderRead(
        id=order.id,
        user_id=order.user_id,
        total_amount=order.total_amount,
        status=order.status,
        created_at=order.created_at,
        items=item_reads,
    )


@router.get(
    "",
    response_model=OrderPagination,
    status_code=status.HTTP_200_OK,
    summary="List orders",
    description="Lists orders with pagination. Returns orders for the authenticated customer, or all orders if Admin.",
)
async def list_orders(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
) -> OrderPagination:
    service = OrderService(session)
    return await service.list_orders(current_user=current_user, page=page, limit=limit)
