"""Tests for GoCardless API agreements module."""

from unittest.mock import MagicMock

import pytest

from src.providers.gocardless.api.agreements import (
    accept_agreement,
    delete_agreement,
    get_all_agreements,
)


class TestGetAllAgreements:
    """Tests for get_all_agreements function."""

    def test_get_all_agreements_success(self, mock_gocardless_credentials: MagicMock) -> None:
        """Test successful agreements retrieval."""
        mock_gocardless_credentials.make_get_request.return_value = {
            "results": [
                {"id": "agr-001", "institution_id": "CHASE_CHASGB2L"},
                {"id": "agr-002", "institution_id": "NATIONWIDE_NAIAGB21"},
            ]
        }

        result = get_all_agreements(mock_gocardless_credentials)

        assert len(result) == 2
        assert result[0]["id"] == "agr-001"
        mock_gocardless_credentials.make_get_request.assert_called_once_with(
            "https://bankaccountdata.gocardless.com/api/v2/agreements/enduser"
        )

    def test_get_all_agreements_empty(self, mock_gocardless_credentials: MagicMock) -> None:
        """Test empty agreements list."""
        mock_gocardless_credentials.make_get_request.return_value = {"results": []}

        result = get_all_agreements(mock_gocardless_credentials)

        assert result == []

    def test_get_all_agreements_invalid_response(
        self, mock_gocardless_credentials: MagicMock
    ) -> None:
        """Test handling of invalid response format."""
        mock_gocardless_credentials.make_get_request.return_value = []

        with pytest.raises(ValueError, match="not in expected format"):
            get_all_agreements(mock_gocardless_credentials)


class TestDeleteAgreement:
    """Tests for delete_agreement function."""

    def test_delete_agreement_success(self, mock_gocardless_credentials: MagicMock) -> None:
        """Test successful agreement deletion."""
        mock_gocardless_credentials.make_delete_request.return_value = {
            "summary": "End User Agreement deleted"
        }

        result = delete_agreement(mock_gocardless_credentials, "agr-001")

        assert result["summary"] == "End User Agreement deleted"
        mock_gocardless_credentials.make_delete_request.assert_called_once_with(
            "https://bankaccountdata.gocardless.com/api/v2/agreements/enduser/agr-001"
        )


class TestAcceptAgreement:
    """Tests for accept_agreement function."""

    def test_accept_agreement_success(self, mock_gocardless_credentials: MagicMock) -> None:
        """Test successful agreement acceptance."""
        mock_gocardless_credentials.make_put_request.return_value = {
            "id": "agr-001",
            "accepted": "2024-01-15T12:00:00Z",
        }

        result = accept_agreement(mock_gocardless_credentials, "agr-001")

        assert result["id"] == "agr-001"
        assert result["accepted"] == "2024-01-15T12:00:00Z"
        mock_gocardless_credentials.make_put_request.assert_called_once_with(
            "https://bankaccountdata.gocardless.com/api/v2/agreements/enduser/agr-001/accept"
        )
