"""Tests for GoCardless API requisition module."""

from unittest.mock import MagicMock

import pytest

from src.providers.gocardless.api.requisition import (
    create_link,
    delete_requisition_data_by_id,
    get_all_requisition_data,
    get_requisition_data_by_id,
)


class TestGetAllRequisitionData:
    """Tests for get_all_requisition_data function."""

    def test_get_all_requisition_data_success(self, mock_gocardless_credentials: MagicMock) -> None:
        """Test successful requisition list retrieval."""
        mock_gocardless_credentials.make_get_request.return_value = {
            "results": [
                {"id": "req-001", "status": "LN"},
                {"id": "req-002", "status": "EX"},
            ]
        }

        result = get_all_requisition_data(mock_gocardless_credentials)

        assert len(result) == 2
        assert result[0]["id"] == "req-001"
        mock_gocardless_credentials.make_get_request.assert_called_once_with(
            "https://bankaccountdata.gocardless.com/api/v2/requisitions"
        )

    def test_get_all_requisition_data_empty(self, mock_gocardless_credentials: MagicMock) -> None:
        """Test empty requisition list."""
        mock_gocardless_credentials.make_get_request.return_value = {"results": []}

        result = get_all_requisition_data(mock_gocardless_credentials)

        assert result == []

    def test_get_all_requisition_data_invalid_response(
        self, mock_gocardless_credentials: MagicMock
    ) -> None:
        """Test handling of invalid response format."""
        mock_gocardless_credentials.make_get_request.return_value = []

        with pytest.raises(ValueError, match="not in expected format"):
            get_all_requisition_data(mock_gocardless_credentials)


class TestGetRequisitionDataById:
    """Tests for get_requisition_data_by_id function."""

    def test_get_requisition_data_by_id_success(
        self, mock_gocardless_credentials: MagicMock
    ) -> None:
        """Test successful requisition retrieval by ID."""
        mock_gocardless_credentials.make_get_request.return_value = {
            "id": "req-001",
            "status": "LN",
            "institution_id": "CHASE_CHASGB2L",
            "accounts": ["acc-001", "acc-002"],
        }

        result = get_requisition_data_by_id(mock_gocardless_credentials, "req-001")

        assert result["id"] == "req-001"
        assert result["status"] == "LN"
        assert len(result["accounts"]) == 2
        mock_gocardless_credentials.make_get_request.assert_called_once_with(
            "https://bankaccountdata.gocardless.com/api/v2/requisitions/req-001"
        )

    def test_get_requisition_data_by_id_invalid_response(
        self, mock_gocardless_credentials: MagicMock
    ) -> None:
        """Test handling of invalid response format."""
        mock_gocardless_credentials.make_get_request.return_value = []

        with pytest.raises(ValueError, match="not in expected format"):
            get_requisition_data_by_id(mock_gocardless_credentials, "req-001")


class TestDeleteRequisitionDataById:
    """Tests for delete_requisition_data_by_id function."""

    def test_delete_requisition_data_by_id_success(
        self, mock_gocardless_credentials: MagicMock
    ) -> None:
        """Test successful requisition deletion."""
        mock_gocardless_credentials.make_delete_request.return_value = {
            "summary": "Requisition deleted"
        }

        result = delete_requisition_data_by_id(mock_gocardless_credentials, "req-001")

        assert result["summary"] == "Requisition deleted"
        mock_gocardless_credentials.make_delete_request.assert_called_once_with(
            "https://bankaccountdata.gocardless.com/api/v2/requisitions/req-001"
        )


class TestCreateLink:
    """Tests for create_link function."""

    def test_create_link_success(self, mock_gocardless_credentials: MagicMock) -> None:
        """Test successful link creation."""
        mock_gocardless_credentials.make_post_request.return_value = {
            "id": "req-new",
            "link": "https://gocardless.com/auth/test",
            "status": "CR",
        }

        result = create_link(
            mock_gocardless_credentials,
            "https://callback.example.com",
            "CHASE_CHASGB2L",
        )

        assert result["id"] == "req-new"
        assert result["link"] == "https://gocardless.com/auth/test"
        mock_gocardless_credentials.make_post_request.assert_called_once_with(
            "https://bankaccountdata.gocardless.com/api/v2/requisitions/",
            body={
                "redirect": "https://callback.example.com",
                "institution_id": "CHASE_CHASGB2L",
            },
        )
