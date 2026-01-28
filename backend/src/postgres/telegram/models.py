"""SQLAlchemy ORM models for Telegram polling state."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.postgres.core import Base


class TelegramLinkCode(Base):
    """ORM model for temporary Telegram link codes.

    When a user wants to link their Telegram account, the API generates
    a one-time code. The user sends this code to the bot, which validates
    it and links the chat_id to their account.

    Codes expire after 10 minutes and are deleted after use.
    """

    __tablename__ = "telegram_link_codes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(8), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_telegram_link_codes_code", "code"),
        Index("idx_telegram_link_codes_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        """Return string representation of the link code."""
        return f"TelegramLinkCode(code={self.code}, user_id={self.user_id})"


class TelegramPollingCursor(Base):
    """ORM model for storing the Telegram polling offset.

    Stores the last processed update_id to ensure no messages are
    missed or duplicated when using long polling.

    There should only ever be one row in this table (id=1).
    """

    __tablename__ = "telegram_polling_cursor"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        default=1,
    )
    last_update_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        """Return string representation of the cursor."""
        return f"TelegramPollingCursor(last_update_id={self.last_update_id})"
