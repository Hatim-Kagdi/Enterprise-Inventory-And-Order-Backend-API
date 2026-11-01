from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description="Validates API operational state and database connectivity.",
)
async def health_check(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> HealthResponse | JSONResponse:
    db_status = "connected"
    http_status = status.HTTP_200_OK

    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"disconnected: {str(exc)}"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    payload = {
        "status": "healthy" if http_status == status.HTTP_200_OK else "unhealthy",
        "database": db_status,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if http_status != status.HTTP_200_OK:
        return JSONResponse(status_code=http_status, content=payload)

    return HealthResponse(
        status="healthy",
        database=db_status,
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc),
    )
