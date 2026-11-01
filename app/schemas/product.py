from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Product title")
    sku: str = Field(..., min_length=1, max_length=100, description="Stock Keeping Unit")
    description: Optional[str] = Field(None, description="Detailed product description")
    price: Decimal = Field(..., gt=Decimal("0.00"), decimal_places=2, description="Unit price")
    stock_quantity: int = Field(default=0, ge=0, description="Available inventory count")
    is_active: bool = Field(default=True, description="Whether product is active for purchase")


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    sku: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=Decimal("0.00"), decimal_places=2)
    stock_quantity: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ProductRead(ProductBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductPagination(BaseModel):
    items: List[ProductRead]
    total: int
    page: int
    limit: int
    total_pages: int
