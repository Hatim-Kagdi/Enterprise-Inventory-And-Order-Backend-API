from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.order import OrderStatus


class OrderItemBase(BaseModel):
    product_id: UUID
    quantity: int = Field(..., gt=0, description="Quantity of items to purchase")


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemRead(OrderItemBase):
    id: UUID
    unit_price: Decimal
    product_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    items: List[OrderItemCreate] = Field(..., min_length=1, description="List of items in the order")


class OrderRead(BaseModel):
    id: UUID
    user_id: UUID
    total_amount: Decimal
    status: OrderStatus
    created_at: datetime
    items: List[OrderItemRead]

    model_config = ConfigDict(from_attributes=True)


class OrderPagination(BaseModel):
    items: List[OrderRead]
    total: int
    page: int
    limit: int
    total_pages: int
