from fastapi import APIRouter
from app.api.v1.endpoints import auth, health, orders, products

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(products.router)
api_router.include_router(orders.router)
api_router.include_router(health.router)
