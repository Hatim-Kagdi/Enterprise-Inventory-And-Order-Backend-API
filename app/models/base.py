from datetime import datetime, timezone
import uuid
from sqlalchemy import DateTime, func, types
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy 2.0 mapped models."""
    pass


class TimestampMixin:
    """Mixin providing created_at with UTC timezone default."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    """Mixin providing UUID as primary key."""

    id: Mapped[uuid.UUID] = mapped_column(
        types.Uuid,
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )
