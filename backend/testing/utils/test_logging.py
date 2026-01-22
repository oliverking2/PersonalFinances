"""Tests for utils logging module."""

import logging
from unittest.mock import MagicMock, patch

from src.utils.logging import setup_dagster_logger


class TestSetupDagsterLogger:
    """Tests for setup_dagster_logger function."""

    @patch("src.utils.logging.get_dagster_logger")
    def test_setup_dagster_logger_returns_logger(self, mock_get_logger: MagicMock) -> None:
        """Test that a logger is returned."""
        mock_logger = MagicMock(spec=logging.Logger)
        mock_get_logger.return_value = mock_logger

        result = setup_dagster_logger("test_module")

        assert result == mock_logger
        mock_get_logger.assert_called_once_with(name="test_module")

    @patch("src.utils.logging.get_dagster_logger")
    def test_setup_dagster_logger_uses_provided_name(self, mock_get_logger: MagicMock) -> None:
        """Test that the provided name is passed to get_dagster_logger."""
        mock_logger = MagicMock(spec=logging.Logger)
        mock_get_logger.return_value = mock_logger

        setup_dagster_logger("custom_logger_name")

        mock_get_logger.assert_called_once_with(name="custom_logger_name")
