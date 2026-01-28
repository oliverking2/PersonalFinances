"""Configuration for Telegram integration using pydantic-settings."""

from enum import StrEnum
from functools import cached_property, lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class TelegramMode(StrEnum):
    """Telegram transport mode."""

    POLLING = "polling"
    WEBHOOK = "webhook"


class TelegramConfig(BaseSettings):
    """Configuration for Telegram integration.

    All settings are loaded from environment variables with the TELEGRAM_ prefix.

    :param bot_token: Telegram bot token from @BotFather.
    :param chat_id: Default chat ID for sending messages (used by alerts).
    :param mode: Transport mode (polling or webhook).
    :param poll_timeout: Timeout in seconds for long polling.
    :param error_retry_delay: Delay in seconds between retries after an error.
    :param max_consecutive_errors: Maximum consecutive errors before backing off.
    :param backoff_delay: Delay in seconds after max consecutive errors.
    :param allowed_chat_ids: Comma-separated list of chat IDs allowed to interact.
    """

    model_config = SettingsConfigDict(
        env_prefix="TELEGRAM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    bot_token: str = Field(..., description="Bot token from @BotFather")
    chat_id: str | None = Field(
        default=None,
        description="Default chat ID for sending messages",
    )
    mode: TelegramMode = Field(
        default=TelegramMode.POLLING,
        description="Transport mode (polling or webhook)",
    )
    poll_timeout: int = Field(
        default=30,
        ge=1,
        le=60,
        description="Long polling timeout in seconds",
    )
    error_retry_delay: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Delay in seconds between retries after an error",
    )
    max_consecutive_errors: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum consecutive errors before backing off",
    )
    backoff_delay: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Delay in seconds after max consecutive errors",
    )
    allowed_chat_ids: str = Field(
        default="",
        description="Comma-separated list of allowed chat IDs",
    )

    @field_validator("allowed_chat_ids")
    @classmethod
    def validate_allowed_chat_ids(cls, v: str) -> str:
        """Validate allowed chat IDs format.

        :param v: Raw comma-separated string from environment.
        :returns: The validated string.
        """
        # Empty is allowed - validation happens at runtime when needed
        return v

    @cached_property
    def allowed_chat_ids_set(self) -> frozenset[str]:
        """Get the allowed chat IDs as a frozenset.

        :returns: Frozenset of allowed chat ID strings.
        """
        if not self.allowed_chat_ids:
            return frozenset()
        return frozenset(
            chat_id.strip() for chat_id in self.allowed_chat_ids.split(",") if chat_id.strip()
        )


@lru_cache
def get_telegram_settings() -> TelegramConfig:
    """Get cached Telegram settings.

    Settings are loaded once and cached for the lifetime of the process.

    :returns: Configured TelegramConfig instance.
    """
    return TelegramConfig()  # type: ignore[call-arg]
