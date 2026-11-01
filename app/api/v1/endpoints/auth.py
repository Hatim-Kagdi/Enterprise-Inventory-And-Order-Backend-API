from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserLogin, UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers a new user account with email, password, and optional role (Admin/Customer).",
)
async def register(
    user_in: UserCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserRead:
    service = AuthService(session)
    user = await service.register(user_in)
    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticates credentials and returns a JWT bearer access token.",
)
async def login(
    login_in: UserLogin,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    service = AuthService(session)
    return await service.authenticate(email=login_in.email, password=login_in.password)


@router.get(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Returns profile information of the currently authenticated user.",
)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserRead:
    return UserRead.model_validate(current_user)
