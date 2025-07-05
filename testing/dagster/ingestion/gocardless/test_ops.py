"""Unit tests for GoCardless Dagster operations."""

import unittest
from unittest.mock import Mock, patch

from dagster import DynamicOutput, build_op_context

from src.dagster.ingestion.gocardless.requisitions.ops import (
    fetch_requisition_ids,
    refresh_and_update_record,
)


class TestGoCardlessDagsterOps(unittest.TestCase):
    """Test cases for GoCardless Dagster operations."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_session = Mock()
        # Create a proper op context with mocked resources
        self.mock_context = build_op_context(resources={"mysql_db": self.mock_session})

    @patch("src.dagster.ingestion.gocardless.ops.get_all_requisition_ids")
    def test_fetch_requisition_ids_success(self, mock_get_ids: Mock) -> None:
        """Test successful fetching of requisition IDs."""
        # Arrange
        expected_ids = ["req_1", "req-2", "req_3"]
        mock_get_ids.return_value = expected_ids

        # Act
        result = list(fetch_requisition_ids(self.mock_context))

        # Assert
        self.assertEqual(len(result), 3)
        for i, dynamic_output in enumerate(result):
            self.assertIsInstance(dynamic_output, DynamicOutput)
            self.assertEqual(dynamic_output.value, expected_ids[i])
            self.assertEqual(dynamic_output.mapping_key, expected_ids[i].replace("-", ""))

        mock_get_ids.assert_called_once_with(self.mock_session)

    @patch("src.dagster.ingestion.gocardless.ops.get_all_requisition_ids")
    def test_fetch_requisition_ids_empty(self, mock_get_ids: Mock) -> None:
        """Test fetching requisition IDs when none exist."""
        # Arrange
        mock_get_ids.return_value = []

        # Act
        result = list(fetch_requisition_ids(self.mock_context))

        # Assert
        self.assertEqual(len(result), 0)
        mock_get_ids.assert_called_once_with(self.mock_session)

    @patch("src.dagster.ingestion.gocardless.ops.get_all_requisition_ids")
    def test_fetch_requisition_ids_single_id(self, mock_get_ids: Mock) -> None:
        """Test fetching a single requisition ID."""
        # Arrange
        expected_ids = ["single_req_id"]
        mock_get_ids.return_value = expected_ids

        # Act
        result = list(fetch_requisition_ids(self.mock_context))

        # Assert
        self.assertEqual(len(result), 1)
        dynamic_output = result[0]
        self.assertIsInstance(dynamic_output, DynamicOutput)
        self.assertEqual(dynamic_output.value, "single_req_id")
        self.assertEqual(dynamic_output.mapping_key, "single_req_id")

    @patch("src.dagster.ingestion.gocardless.ops.update_requisition_record")
    @patch("src.dagster.ingestion.gocardless.ops.fetch_requisition_data_by_id")
    @patch("src.dagster.ingestion.gocardless.ops.GoCardlessCredentials")
    def test_refresh_and_update_record_success(
        self, mock_creds_class: Mock, mock_fetch_data: Mock, mock_update_record: Mock
    ) -> None:
        """Test successful refresh and update of a requisition record."""
        # Arrange
        req_id = "test_req_id"
        mock_creds = Mock()
        mock_creds_class.return_value = mock_creds

        api_data = {"id": req_id, "status": "LN", "updated": "2023-06-22T10:00:00Z"}
        mock_fetch_data.return_value = api_data
        mock_update_record.return_value = True

        # Act
        refresh_and_update_record(self.mock_context, req_id)

        # Assert
        mock_creds_class.assert_called_once()
        mock_fetch_data.assert_called_once_with(mock_creds, req_id)
        mock_update_record.assert_called_once_with(self.mock_session, req_id, api_data)

    @patch("src.dagster.ingestion.gocardless.ops.update_requisition_record")
    @patch("src.dagster.ingestion.gocardless.ops.fetch_requisition_data_by_id")
    @patch("src.dagster.ingestion.gocardless.ops.GoCardlessCredentials")
    def test_refresh_and_update_record_api_error(
        self, mock_creds_class: Mock, mock_fetch_data: Mock, mock_update_record: Mock
    ) -> None:
        """Test refresh and update when API call fails."""
        # Arrange
        req_id = "test_req_id"
        mock_creds = Mock()
        mock_creds_class.return_value = mock_creds

        mock_fetch_data.side_effect = Exception("API Error")

        # Act
        refresh_and_update_record(self.mock_context, req_id)

        # Assert
        mock_creds_class.assert_called_once()
        mock_fetch_data.assert_called_once_with(mock_creds, req_id)
        mock_update_record.assert_not_called()

    @patch("src.dagster.ingestion.gocardless.ops.update_requisition_record")
    @patch("src.dagster.ingestion.gocardless.ops.fetch_requisition_data_by_id")
    @patch("src.dagster.ingestion.gocardless.ops.GoCardlessCredentials")
    def test_refresh_and_update_record_no_data(
        self, mock_creds_class: Mock, mock_fetch_data: Mock, mock_update_record: Mock
    ) -> None:
        """Test refresh and update when API returns no data."""
        # Arrange
        req_id = "test_req_id"
        mock_creds = Mock()
        mock_creds_class.return_value = mock_creds

        mock_fetch_data.return_value = None

        # Act
        refresh_and_update_record(self.mock_context, req_id)

        # Assert
        mock_creds_class.assert_called_once()
        mock_fetch_data.assert_called_once_with(mock_creds, req_id)
        mock_update_record.assert_not_called()

    @patch("src.dagster.ingestion.gocardless.ops.update_requisition_record")
    @patch("src.dagster.ingestion.gocardless.ops.fetch_requisition_data_by_id")
    @patch("src.dagster.ingestion.gocardless.ops.GoCardlessCredentials")
    def test_refresh_and_update_record_empty_data(
        self, mock_creds_class: Mock, mock_fetch_data: Mock, mock_update_record: Mock
    ) -> None:
        """Test refresh and update when API returns empty data."""
        # Arrange
        req_id = "test_req_id"
        mock_creds = Mock()
        mock_creds_class.return_value = mock_creds

        mock_fetch_data.return_value = {}

        # Act
        refresh_and_update_record(self.mock_context, req_id)

        # Assert
        mock_creds_class.assert_called_once()
        mock_fetch_data.assert_called_once_with(mock_creds, req_id)
        mock_update_record.assert_not_called()

    @patch("src.dagster.ingestion.gocardless.ops.update_requisition_record")
    @patch("src.dagster.ingestion.gocardless.ops.fetch_requisition_data_by_id")
    @patch("src.dagster.ingestion.gocardless.ops.GoCardlessCredentials")
    def test_refresh_and_update_record_update_fails(
        self, mock_creds_class: Mock, mock_fetch_data: Mock, mock_update_record: Mock
    ) -> None:
        """Test refresh and update when database update fails."""
        # Arrange
        req_id = "test_req_id"
        mock_creds = Mock()
        mock_creds_class.return_value = mock_creds

        api_data = {"id": req_id, "status": "LN", "updated": "2023-06-22T10:00:00Z"}
        mock_fetch_data.return_value = api_data
        mock_update_record.return_value = False  # Update fails

        # Act
        refresh_and_update_record(self.mock_context, req_id)

        # Assert
        mock_creds_class.assert_called_once()
        mock_fetch_data.assert_called_once_with(mock_creds, req_id)
        mock_update_record.assert_called_once_with(self.mock_session, req_id, api_data)

    def test_refresh_and_update_record_different_req_ids(self) -> None:
        """Test refresh and update with different requisition ID formats."""
        test_req_ids = [
            "simple_id",
            "id-with-dashes",
            "id_with_underscores",
            "123456789",
            "mixed-id_123",
        ]

        with (
            patch("src.dagster.ingestion.gocardless.ops.GoCardlessCredentials") as mock_creds_class,
            patch(
                "src.dagster.ingestion.gocardless.ops.fetch_requisition_data_by_id"
            ) as mock_fetch_data,
            patch(
                "src.dagster.ingestion.gocardless.ops.update_requisition_record"
            ) as mock_update_record,
        ):
            mock_creds = Mock()
            mock_creds_class.return_value = mock_creds
            mock_fetch_data.return_value = {"id": "test", "status": "LN"}
            mock_update_record.return_value = True

            for req_id in test_req_ids:
                with self.subTest(req_id=req_id):
                    # Reset mocks
                    mock_fetch_data.reset_mock()
                    mock_update_record.reset_mock()

                    # Act
                    refresh_and_update_record(self.mock_context, req_id)

                    # Assert
                    mock_fetch_data.assert_called_once_with(mock_creds, req_id)


if __name__ == "__main__":
    unittest.main()
