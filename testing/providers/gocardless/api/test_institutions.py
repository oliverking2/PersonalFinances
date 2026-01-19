"""Tests for GoCardless API institutions module."""

from unittest.mock import MagicMock

import pytest

from src.providers.gocardless.api.institutions import (
    get_institution_mapping,
    get_institutions,
)


class TestGetInstitutions:
    """Tests for get_institutions function."""

    def test_get_institutions_success(self, mock_gocardless_credentials: MagicMock) -> None:
        """Test successful institutions retrieval."""
        mock_gocardless_credentials.make_get_request.return_value = [
            {"id": "CHASE_CHASGB2L", "name": "Chase", "countries": ["GB"]},
            {"id": "NATIONWIDE_NAIAGB21", "name": "Nationwide", "countries": ["GB"]},
        ]

        result = get_institutions(mock_gocardless_credentials)

        assert len(result) == 2
        assert result[0]["id"] == "CHASE_CHASGB2L"
        mock_gocardless_credentials.make_get_request.assert_called_once_with(
            "https://bankaccountdata.gocardless.com/api/v2/institutions",
            params={"country": "gb"},
        )

    def test_get_institutions_empty_list(self, mock_gocardless_credentials: MagicMock) -> None:
        """Test empty institutions list."""
        mock_gocardless_credentials.make_get_request.return_value = []

        result = get_institutions(mock_gocardless_credentials)

        assert result == []

    def test_get_institutions_invalid_response(
        self, mock_gocardless_credentials: MagicMock
    ) -> None:
        """Test handling of invalid response format."""
        mock_gocardless_credentials.make_get_request.return_value = {"error": "Invalid"}

        with pytest.raises(ValueError, match="not in expected format"):
            get_institutions(mock_gocardless_credentials)


class TestGetInstitutionMapping:
    """Tests for get_institution_mapping function."""

    def test_get_institution_mapping_success(self, mock_gocardless_credentials: MagicMock) -> None:
        """Test successful institution mapping retrieval."""
        mock_gocardless_credentials.make_get_request.return_value = [
            {"id": "CHASE_CHASGB2L", "name": "Chase"},
            {"id": "NATIONWIDE_NAIAGB21", "name": "Nationwide"},
            {"id": "AMERICAN_EXPRESS_AESUGB21", "name": "American Express"},
        ]

        result = get_institution_mapping(mock_gocardless_credentials)

        assert result == {
            "Chase": "CHASE_CHASGB2L",
            "Nationwide": "NATIONWIDE_NAIAGB21",
            "American Express": "AMERICAN_EXPRESS_AESUGB21",
        }

    def test_get_institution_mapping_empty(self, mock_gocardless_credentials: MagicMock) -> None:
        """Test empty institution mapping."""
        mock_gocardless_credentials.make_get_request.return_value = []

        result = get_institution_mapping(mock_gocardless_credentials)

        assert result == {}
