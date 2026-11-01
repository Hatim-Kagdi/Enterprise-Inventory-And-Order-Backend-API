from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import (
    AuthenticationFailedException,
    ConflictException,
    EntityNotFoundException,
)
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import Token, UserCreate


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)

    async def register(self, user_in: UserCreate) -> User:
        """Registers a new user after verifying email uniqueness."""
        normalized_email = user_in.email.lower().strip()
        existing_user = await self.user_repo.get_by_email(normalized_email)
        if existing_user:
            raise ConflictException(
                message=f"User with email '{normalized_email}' already exists",
                details={"email": normalized_email},
            )

        user = User(
            email=normalized_email,
            hashed_password=get_password_hash(user_in.password),
            role=user_in.role,
        )

        created_user = await self.user_repo.create(user)
        await self.session.commit()
        await self.session.refresh(created_user)
        return created_user

    async def authenticate(self, email: str, password: str) -> Token:
        """Validates credentials and issues a signed JWT access token."""
        normalized_email = email.lower().strip()
        user = await self.user_repo.get_by_email(normalized_email)

        if not user or not verify_password(password, user.hashed_password):
            raise AuthenticationFailedException(
                message="Incorrect email or password",
            )

        token_str = create_access_token(
            subject=str(user.id),
            role=user.role.value,
        )

        return Token(access_token=token_str, token_type="bearer")

    async def get_user_by_id(self, user_id: UUID) -> User:
        """Retrieves user by primary key or raises 404."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)
        return user
