"""Unit tests for MySQL operations."""

import unittest
from typing import Dict
from unittest.mock import Mock
from datetime import datetime

from src.mysql.gocardless.operations import get_all_requisition_ids, update_requisition_record


class TestMySQLOperations(unittest.TestCase):
    """Test cases for MySQL database operations."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_session = Mock()

    def test_get_all_requisition_ids_success(self) -> None:
        """Test successful retrieval of requisition IDs."""
        # Arrange
        expected_ids = ["req_1", "req_2", "req_3"]
        # Mock the query result - SQLAlchemy returns tuples
        self.mock_session.query.return_value.all.return_value = [(id_,) for id_ in expected_ids]

        # Act
        result = get_all_requisition_ids(self.mock_session)

        # Assert
        self.assertEqual(result, expected_ids)
        self.mock_session.query.assert_called_once()

    def test_get_all_requisition_ids_empty(self) -> None:
        """Test retrieval when no requisition IDs exist."""
        # Arrange
        self.mock_session.query.return_value.all.return_value = []

        # Act
        result = get_all_requisition_ids(self.mock_session)

        # Assert
        self.assertEqual(result, [])
        self.mock_session.query.assert_called_once()

    def test_update_requisition_record_success(self) -> None:
        """Test successful update of a requisition record."""
        # Arrange
        requisition_id = "test_req_id"
        update_data = {"status": "LN", "redirect": "http://example.com"}
        mock_obj = Mock()
        mock_obj.status = "CR"
        mock_obj.redirect = "http://old.com"
        self.mock_session.get.return_value = mock_obj

        # Act
        result = update_requisition_record(self.mock_session, requisition_id, update_data)

        # Assert
        self.assertTrue(result)
        self.mock_session.get.assert_called_once_with(unittest.mock.ANY, requisition_id)
        self.assertEqual(mock_obj.status, "LN")
        self.assertEqual(mock_obj.redirect, "http://example.com")
        # The updated field should be set to current datetime (not from data)
        self.assertIsInstance(mock_obj.updated, datetime)
        self.mock_session.commit.assert_called_once()

    def test_update_requisition_record_not_found(self) -> None:
        """Test update when requisition record is not found."""
        # Arrange
        requisition_id = "nonexistent_req_id"
        update_data = {"status": "LN"}
        self.mock_session.get.return_value = None

        # Act
        result = update_requisition_record(self.mock_session, requisition_id, update_data)

        # Assert
        self.assertFalse(result)
        self.mock_session.get.assert_called_once_with(unittest.mock.ANY, requisition_id)
        self.mock_session.commit.assert_not_called()

    def test_update_requisition_record_invalid_field(self) -> None:
        """Test update with invalid field that doesn't exist on the model."""
        # Arrange
        requisition_id = "test_req_id"
        update_data = {"status": "LN", "invalid_field": "some_value"}
        mock_obj = Mock()
        mock_obj.status = "CR"

        self.mock_session.get.return_value = mock_obj

        result = update_requisition_record(self.mock_session, requisition_id, update_data)

        # Assert
        self.assertTrue(result)
        self.assertEqual(mock_obj.status, "LN")
        # The function should still succeed and commit even with invalid fields
        # (they are just ignored as per the implementation)
        self.mock_session.commit.assert_called_once()

    def test_update_requisition_record_empty_data(self) -> None:
        """Test update with empty data dictionary."""
        # Arrange
        requisition_id = "test_req_id"
        update_data: Dict[str, str] = {}
        mock_obj = Mock()
        self.mock_session.get.return_value = mock_obj

        # Act
        result = update_requisition_record(self.mock_session, requisition_id, update_data)

        # Assert
        self.assertTrue(result)
        self.mock_session.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
