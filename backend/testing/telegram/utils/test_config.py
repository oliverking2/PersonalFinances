"""Tests for Telegram configuration module."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.telegram.utils.config import TelegramConfig, TelegramMode, get_telegram_settings


class TestTelegramConfig:
    """Tests for TelegramConfig."""

    def test_valid_settings(self) -> None:
        """Test creating config with valid settings."""
        config = TelegramConfig(
            bot_token="test-token",
            chat_id="12345",
            poll_timeout=30,
        )

        assert config.bot_token == "test-token"
        assert config.chat_id == "12345"
        assert config.poll_timeout == 30
        assert config.mode == TelegramMode.POLLING

    def test_default_values(self) -> None:
        """Test default values are applied."""
        config = TelegramConfig(bot_token="test-token")

        assert config.chat_id is None
        assert config.mode == TelegramMode.POLLING
        assert config.poll_timeout == 30
        assert config.error_retry_delay == 5
        assert config.max_consecutive_errors == 5
        assert config.backoff_delay == 30
        assert config.allowed_chat_ids == ""

    def test_missing_bot_token_raises_error(self) -> None:
        """Test that missing bot_token raises validation error."""
        # Ensure TELEGRAM_BOT_TOKEN is not in environment (BaseSettings reads from env)
        # Also patch model_config to avoid reading from .env file
        env_without_token = {k: v for k, v in os.environ.items() if k != "TELEGRAM_BOT_TOKEN"}
        with (
            patch.dict(os.environ, env_without_token, clear=True),
            patch.object(
                TelegramConfig, "model_config", {**TelegramConfig.model_config, "env_file": None}
            ),
            pytest.raises(ValidationError),
        ):
            TelegramConfig()  # type: ignore[call-arg]

    def test_poll_timeout_validation_min(self) -> None:
        """Test that poll_timeout below minimum raises error."""
        with pytest.raises(ValidationError):
            TelegramConfig(bot_token="test-token", poll_timeout=0)

    def test_poll_timeout_validation_max(self) -> None:
        """Test that poll_timeout above maximum raises error."""
        with pytest.raises(ValidationError):
            TelegramConfig(bot_token="test-token", poll_timeout=100)

    def test_allowed_chat_ids_set_empty(self) -> None:
        """Test allowed_chat_ids_set with empty string."""
        config = TelegramConfig(bot_token="test-token", allowed_chat_ids="")

        assert config.allowed_chat_ids_set == frozenset()

    def test_allowed_chat_ids_set_single(self) -> None:
        """Test allowed_chat_ids_set with single ID."""
        config = TelegramConfig(bot_token="test-token", allowed_chat_ids="12345")

        assert config.allowed_chat_ids_set == frozenset(["12345"])

    def test_allowed_chat_ids_set_multiple(self) -> None:
        """Test allowed_chat_ids_set with multiple IDs."""
        config = TelegramConfig(bot_token="test-token", allowed_chat_ids="12345,67890")

        assert config.allowed_chat_ids_set == frozenset(["12345", "67890"])

    def test_allowed_chat_ids_set_whitespace_handling(self) -> None:
        """Test that whitespace is trimmed from chat IDs."""
        config = TelegramConfig(bot_token="test-token", allowed_chat_ids=" 12345 , 67890 ")

        assert config.allowed_chat_ids_set == frozenset(["12345", "67890"])

    def test_mode_enum(self) -> None:
        """Test mode can be set to different values."""
        polling_config = TelegramConfig(bot_token="test-token", mode=TelegramMode.POLLING)
        webhook_config = TelegramConfig(bot_token="test-token", mode=TelegramMode.WEBHOOK)

        assert polling_config.mode == TelegramMode.POLLING
        assert webhook_config.mode == TelegramMode.WEBHOOK


class TestGetTelegramSettings:
    """Tests for get_telegram_settings function."""

    def test_settings_from_environment(self) -> None:
        """Test that settings are loaded from environment."""
        env_vars = {
            "TELEGRAM_BOT_TOKEN": "env-token",
            "TELEGRAM_CHAT_ID": "99999",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            # Clear the cache to force reload
            get_telegram_settings.cache_clear()

            settings = get_telegram_settings()

            assert settings.bot_token == "env-token"
            assert settings.chat_id == "99999"

        # Clear cache after test
        get_telegram_settings.cache_clear()

    def test_settings_with_all_env_vars(self) -> None:
        """Test settings with all environment variables set."""
        env_vars = {
            "TELEGRAM_BOT_TOKEN": "full-token",
            "TELEGRAM_CHAT_ID": "88888",
            "TELEGRAM_POLL_TIMEOUT": "45",
            "TELEGRAM_ALLOWED_CHAT_IDS": "111,222,333",
            "TELEGRAM_ERROR_RETRY_DELAY": "10",
            "TELEGRAM_MAX_CONSECUTIVE_ERRORS": "10",
            "TELEGRAM_BACKOFF_DELAY": "60",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            get_telegram_settings.cache_clear()

            settings = get_telegram_settings()

            assert settings.bot_token == "full-token"
            assert settings.chat_id == "88888"
            assert settings.poll_timeout == 45
            assert settings.allowed_chat_ids == "111,222,333"
            assert settings.allowed_chat_ids_set == frozenset(["111", "222", "333"])
            assert settings.error_retry_delay == 10
            assert settings.max_consecutive_errors == 10
            assert settings.backoff_delay == 60

        get_telegram_settings.cache_clear()

    def test_settings_caching(self) -> None:
        """Test that settings are cached."""
        env_vars = {"TELEGRAM_BOT_TOKEN": "cached-token"}

        with patch.dict(os.environ, env_vars, clear=False):
            get_telegram_settings.cache_clear()

            settings1 = get_telegram_settings()
            settings2 = get_telegram_settings()

            # Should be the same object due to caching
            assert settings1 is settings2

        get_telegram_settings.cache_clear()
