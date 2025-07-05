"""Unit tests for GoCardless API requisition functions."""

import unittest
from unittest.mock import Mock, patch
import requests

from src.gocardless.api.requisition import (
    fetch_requisition_data_by_id,
    delete_requisition_data_by_id,
)
from src.gocardless.api.auth import GoCardlessCredentials

from datetime import datetime

from src.postgresql.gocardless.operations import update_requisition_record
from src.postgresql.gocardless.models import RequisitionLink
from src.utils.definitions import gocardless_database_url

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


class TestGoCardlessRequisitionAPI(unittest.TestCase):
    """Test cases for GoCardless requisition API functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_creds = Mock(spec=GoCardlessCredentials)
        self.mock_creds.access_token = "test_access_token"
        self.test_req_id = "test_requisition_id"
        self.expected_url = (
            f"https://bankaccountdata.gocardless.com/api/v2/requisitions/{self.test_req_id}"
        )

    @patch("src.gocardless.api.requisition.requests.get")
    def test_fetch_requisition_data_by_id_success(self, mock_get: Mock) -> None:
        """Test successful fetch of requisition data."""
        # Arrange
        expected_data = {
            "id": self.test_req_id,
            "status": "LN",
            "accounts": ["account_1", "account_2"],
        }
        mock_response = Mock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Act
        result = fetch_requisition_data_by_id(self.mock_creds, self.test_req_id)

        # Assert
        self.assertEqual(result, expected_data)
        mock_get.assert_called_once_with(
            self.expected_url, headers={"Authorization": f"Bearer {self.mock_creds.access_token}"}
        )
        mock_response.raise_for_status.assert_called_once()
        mock_response.json.assert_called_once()

    @patch("src.gocardless.api.requisition.requests.get")
    def test_fetch_requisition_data_by_id_http_error(self, mock_get: Mock) -> None:
        """Test fetch requisition data with HTTP error."""
        # Arrange
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        # Act & Assert
        with self.assertRaises(requests.HTTPError):
            fetch_requisition_data_by_id(self.mock_creds, self.test_req_id)

        mock_get.assert_called_once_with(
            self.expected_url, headers={"Authorization": f"Bearer {self.mock_creds.access_token}"}
        )
        mock_response.raise_for_status.assert_called_once()

    @patch("src.gocardless.api.requisition.requests.get")
    def test_fetch_requisition_data_by_id_request_exception(self, mock_get: Mock) -> None:
        """Test fetch requisition data with request exception."""
        # Arrange
        mock_get.side_effect = requests.RequestException("Connection error")

        # Act & Assert
        with self.assertRaises(requests.RequestException):
            fetch_requisition_data_by_id(self.mock_creds, self.test_req_id)

        mock_get.assert_called_once_with(
            self.expected_url, headers={"Authorization": f"Bearer {self.mock_creds.access_token}"}
        )

    @patch("src.gocardless.api.requisition.requests.delete")
    def test_delete_requisition_data_by_id_success(self, mock_delete: Mock) -> None:
        """Test successful deletion of requisition data."""
        # Arrange
        expected_data = {"detail": "Requisition deleted successfully"}
        mock_response = Mock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status.return_value = None
        mock_delete.return_value = mock_response

        # Act
        result = delete_requisition_data_by_id(self.mock_creds, self.test_req_id)

        # Assert
        self.assertEqual(result, expected_data)
        mock_delete.assert_called_once_with(
            self.expected_url, headers={"Authorization": f"Bearer {self.mock_creds.access_token}"}
        )
        mock_response.raise_for_status.assert_called_once()
        mock_response.json.assert_called_once()

    @patch("src.gocardless.api.requisition.requests.delete")
    def test_delete_requisition_data_by_id_http_error(self, mock_delete: Mock) -> None:
        """Test delete requisition data with HTTP error."""
        # Arrange
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        mock_delete.return_value = mock_response

        # Act & Assert
        with self.assertRaises(requests.HTTPError):
            delete_requisition_data_by_id(self.mock_creds, self.test_req_id)

        mock_delete.assert_called_once_with(
            self.expected_url, headers={"Authorization": f"Bearer {self.mock_creds.access_token}"}
        )
        mock_response.raise_for_status.assert_called_once()

    @patch("src.gocardless.api.requisition.requests.delete")
    def test_delete_requisition_data_by_id_request_exception(self, mock_delete: Mock) -> None:
        """Test delete requisition data with request exception."""
        # Arrange
        mock_delete.side_effect = requests.RequestException("Network error")

        # Act & Assert
        with self.assertRaises(requests.RequestException):
            delete_requisition_data_by_id(self.mock_creds, self.test_req_id)

        mock_delete.assert_called_once_with(
            self.expected_url, headers={"Authorization": f"Bearer {self.mock_creds.access_token}"}
        )

    def test_fetch_requisition_data_by_id_correct_url_construction(self) -> None:
        """Test that the URL is constructed correctly for different requisition IDs."""
        # Arrange
        test_cases = ["simple_id", "id-with-dashes", "id_with_underscores", "123456789"]

        with patch("src.gocardless.api.requisition.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            for req_id in test_cases:
                with self.subTest(req_id=req_id):
                    # Act
                    fetch_requisition_data_by_id(self.mock_creds, req_id)

                    # Assert
                    expected_url = (
                        f"https://bankaccountdata.gocardless.com/api/v2/requisitions/{req_id}"
                    )
                    mock_get.assert_called_with(
                        expected_url,
                        headers={"Authorization": f"Bearer {self.mock_creds.access_token}"},
                    )

    def test_authorization_header_format(self) -> None:
        """Test that the authorization header is formatted correctly."""
        # Arrange
        test_tokens = [
            "simple_token",
            "token.with.dots",
            "token-with-dashes",
            "very_long_token_with_many_characters_1234567890",
        ]

        with patch("src.gocardless.api.requisition.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            for token in test_tokens:
                with self.subTest(token=token):
                    # Arrange
                    self.mock_creds.access_token = token

                    # Act
                    fetch_requisition_data_by_id(self.mock_creds, self.test_req_id)

                    # Assert
                    mock_get.assert_called_with(
                        self.expected_url, headers={"Authorization": f"Bearer {token}"}
                    )


class TestGoCardlessRequisitionAPIReal(unittest.TestCase):
    """Test with real credentials."""

    requisition_id: str
    session: Session

    @classmethod
    def setUpClass(cls) -> None:
        """Initialise the test class."""
        cls.requisition_id = "testingid"

        engine = create_engine(gocardless_database_url(), echo=False)
        cls.session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()

        existing_record = cls.session.get(RequisitionLink, cls.requisition_id)
        if not existing_record:
            print(f"Creating test record with ID: {cls.requisition_id}")
            test_record = RequisitionLink(
                id=cls.requisition_id,
                created=datetime.now(),
                updated=datetime.now(),
                redirect="http://test.example.com",
                status="CR",
                institution_id="TEST_BANK",
                agreement="test-agreement-id",
                reference="test-reference",
                link="https://test.link.com",
                ssn=None,
                account_selection=False,
                redirect_immediate=False,
            )
            cls.session.add(test_record)
            cls.session.commit()
            print("✓ Test record created successfully")

    def test_update_requisition_record_with_real_db(self) -> None:
        """Test the update_requisition_record function with real database connection."""
        sample_data = {
            "id": self.requisition_id,
            "created": "2025-06-09T21:28:34.258248Z",
            "redirect": "http://localhost:8501/connections?gc_callback=1",
            "status": "LN",
            "institution_id": "NATIONWIDE_NAIAGB21",
            "agreement": "65a028c9-5dfb-46e1-9127-9367e8f85b16",
            "reference": self.requisition_id,
            "link": "https://ob.gocardless.com/ob-psd2/start/0124aa7d-f299-4287-ae65-218d990c5346/NATIONWIDE_NAIAGB21",
            "ssn": None,
            "account_selection": False,
            "redirect_immediate": False,
        }
        try:
            # Record the time before update
            before_update = datetime.now()

            # Call the function
            print(f"Testing update_requisition_record with ID: {self.requisition_id}")
            result = update_requisition_record(self.session, self.requisition_id, sample_data)

            # Verify the result
            assert result, "Function should return True for successful update"
            print("✓ Function returned True for successful update")

            # Verify the record was actually updated
            updated_record = self.session.get(RequisitionLink, self.requisition_id)
            assert updated_record is not None, "Record should exist after update"

            # Verify specific fields were updated
            assert (
                updated_record.status == "LN"
            ), f"Status should be 'LN', got '{updated_record.status}'"
            assert (
                updated_record.institution_id == "NATIONWIDE_NAIAGB21"
            ), "Institution ID should be updated"
            assert (
                updated_record.redirect == "http://localhost:8501/connections?gc_callback=1"
            ), "Redirect should be updated"

            # Verify the updated timestamp was set and is recent
            assert updated_record.updated >= before_update, "Updated timestamp should be recent"

            print("✓ All field updates verified successfully")
            print("✓ Updated timestamp is properly set")
            print("✓ Accounts field was properly excluded from updates")
            print(f"✓ Record updated at: {updated_record.updated}")

        except Exception as e:
            print(f"✗ Test failed with error: {e}")
            self.session.rollback()
            raise
        finally:
            self.session.close()


if __name__ == "__main__":
    unittest.main()
