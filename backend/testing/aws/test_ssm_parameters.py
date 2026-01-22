"""Tests for AWS SSM Parameters module."""

from unittest.mock import MagicMock

import pytest

from src.aws.ssm_parameters import get_parameter_data_from_ssm


class TestGetParameterDataFromSsm:
    """Tests for get_parameter_data_from_ssm function."""

    def test_get_parameter_data_success(self, mock_ssm_client: MagicMock) -> None:
        """Test successful parameter retrieval."""
        mock_ssm_client.get_parameter.return_value = {"Parameter": {"Value": "secret-value"}}

        result = get_parameter_data_from_ssm(mock_ssm_client, "/app/secret")

        assert result == "secret-value"
        mock_ssm_client.get_parameter.assert_called_once_with(
            Name="/app/secret", WithDecryption=True
        )

    def test_get_parameter_data_not_found(self, mock_ssm_client: MagicMock) -> None:
        """Test parameter not found handling."""
        mock_ssm_client.exceptions.ParameterNotFound = Exception
        mock_ssm_client.get_parameter.side_effect = mock_ssm_client.exceptions.ParameterNotFound(
            "Parameter not found"
        )

        with pytest.raises(Exception):
            get_parameter_data_from_ssm(mock_ssm_client, "/app/missing")

    def test_get_parameter_data_other_error(self, mock_ssm_client: MagicMock) -> None:
        """Test other errors are re-raised."""
        mock_ssm_client.exceptions.ParameterNotFound = type("ParameterNotFound", (Exception,), {})
        mock_ssm_client.get_parameter.side_effect = RuntimeError("Connection failed")

        with pytest.raises(RuntimeError, match="Connection failed"):
            get_parameter_data_from_ssm(mock_ssm_client, "/app/param")
