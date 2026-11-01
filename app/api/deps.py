from typing import Annotated
from uuid import UUID
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.exceptions import AuthenticationFailedException, PermissionDeniedException
from app.core.security import decode_access_token
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Dependency that extracts and validates JWT token, returning the authenticated user."""
    payload = decode_access_token(token)
    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise AuthenticationFailedException("Token subject claim missing")

    try:
        user_id = UUID(user_id_str)
    except ValueError as exc:
        raise AuthenticationFailedException("Malformed user ID in token") from exc

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise AuthenticationFailedException("User not found or account deactivated")

    return user


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Enforces administrator role for protected endpoints."""
    if current_user.role != UserRole.ADMIN:
        raise PermissionDeniedException("Administrator access required for this action")
    return current_user
