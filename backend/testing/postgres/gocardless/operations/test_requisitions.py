"""Tests for GoCardless requisition database operations."""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from src.postgres.gocardless.models import RequisitionLink
from src.postgres.gocardless.operations.requisitions import (
    add_requisition_link,
    create_new_requisition_link,
    fetch_all_requisition_ids,
    fetch_requisition_links,
    update_requisition_record,
    upsert_requisition_status,
    upsert_requisitions,
)
from testing.conftest import build_gocardless_requisition_response


class TestFetchRequisitionLinks:
    """Tests for fetch_requisition_links function."""

    def test_fetch_requisition_links_success(
        self, db_session: Session, test_requisition_link: RequisitionLink
    ) -> None:
        """Test successful retrieval of requisition links."""
        result = fetch_requisition_links(db_session)

        assert len(result) == 1
        assert result[0].id == test_requisition_link.id

    def test_fetch_requisition_links_empty(self, db_session: Session) -> None:
        """Test retrieval when no links exist."""
        result = fetch_requisition_links(db_session)

        assert result == []


class TestFetchAllRequisitionIds:
    """Tests for fetch_all_requisition_ids function."""

    def test_fetch_all_requisition_ids_success(
        self, db_session: Session, test_requisition_link: RequisitionLink
    ) -> None:
        """Test successful retrieval of requisition IDs."""
        result = fetch_all_requisition_ids(db_session)

        assert len(result) == 1
        assert result[0] == test_requisition_link.id

    def test_fetch_all_requisition_ids_empty(self, db_session: Session) -> None:
        """Test retrieval when no links exist."""
        result = fetch_all_requisition_ids(db_session)

        assert result == []


class TestAddRequisitionLink:
    """Tests for add_requisition_link function."""

    def test_add_requisition_link_success(self, db_session: Session) -> None:
        """Test successful addition of requisition link."""
        data = build_gocardless_requisition_response(requisition_id="new-req-id")

        result = add_requisition_link(db_session, data, "My Chase Account")

        assert result.id == "new-req-id"
        assert result.friendly_name == "My Chase Account"
        assert result.status == "LN"

        # Verify it's in the database
        stored = db_session.get(RequisitionLink, "new-req-id")
        assert stored is not None
        assert stored.friendly_name == "My Chase Account"


class TestUpdateRequisitionRecord:
    """Tests for update_requisition_record function."""

    def test_update_requisition_record_success(
        self, db_session: Session, test_requisition_link: RequisitionLink
    ) -> None:
        """Test successful update of requisition record."""
        result = update_requisition_record(db_session, test_requisition_link.id, {"status": "EX"})

        assert result is True
        updated = db_session.get(RequisitionLink, test_requisition_link.id)
        assert updated is not None
        assert updated.status == "EX"

    def test_update_requisition_record_not_found(self, db_session: Session) -> None:
        """Test update of non-existent record."""
        result = update_requisition_record(db_session, "non-existent-id", {"status": "EX"})

        assert result is False

    def test_update_requisition_record_ignores_invalid_fields(
        self, db_session: Session, test_requisition_link: RequisitionLink
    ) -> None:
        """Test that invalid fields are ignored during update."""
        result = update_requisition_record(
            db_session,
            test_requisition_link.id,
            {"status": "EX", "invalid_field": "value", "id": "new-id"},
        )

        assert result is True
        updated = db_session.get(RequisitionLink, test_requisition_link.id)
        assert updated is not None
        assert updated.status == "EX"
        # ID should not have changed
        assert updated.id == test_requisition_link.id


class TestUpsertRequisitionStatus:
    """Tests for upsert_requisition_status function."""

    def test_upsert_updates_existing(
        self, db_session: Session, test_requisition_link: RequisitionLink
    ) -> None:
        """Test that existing record is updated."""
        result = upsert_requisition_status(db_session, test_requisition_link.id, "EX")

        assert result.id == test_requisition_link.id
        assert result.status == "EX"

    def test_upsert_creates_new(self, db_session: Session) -> None:
        """Test that new record is created if not exists."""
        result = upsert_requisition_status(db_session, "brand-new-id", "CR")

        assert result.id == "brand-new-id"
        assert result.status == "CR"

        # Verify it's in the database
        stored = db_session.get(RequisitionLink, "brand-new-id")
        assert stored is not None


class TestCreateNewRequisitionLink:
    """Tests for create_new_requisition_link function."""

    @patch("src.postgres.gocardless.operations.requisitions.create_link")
    def test_create_new_requisition_link_success(
        self, mock_create_link: MagicMock, db_session: Session
    ) -> None:
        """Test successful creation of new requisition link."""
        mock_create_link.return_value = build_gocardless_requisition_response(
            requisition_id="api-created-id"
        )
        mock_creds = MagicMock()

        with patch.dict("os.environ", {"GC_CALLBACK_URL": "https://callback.test.com"}):
            result = create_new_requisition_link(
                db_session, mock_creds, "CHASE_CHASGB2L", "My New Account"
            )

        assert result.id == "api-created-id"
        assert result.friendly_name == "My New Account"
        mock_create_link.assert_called_once_with(
            mock_creds, "https://callback.test.com", "CHASE_CHASGB2L"
        )

    def test_create_new_requisition_link_missing_env_var(self, db_session: Session) -> None:
        """Test that missing callback URL raises KeyError."""
        mock_creds = MagicMock()

        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(KeyError, match="GC_CALLBACK_URL"),
        ):
            create_new_requisition_link(db_session, mock_creds, "CHASE_CHASGB2L", "My Account")


class TestUpsertRequisitions:
    """Tests for upsert_requisitions function."""

    def test_upsert_empty_list_returns_zero(self, db_session: Session) -> None:
        """Test that empty list returns 0 without errors."""
        result = upsert_requisitions(db_session, [])

        assert result == 0

    def test_upsert_updates_existing_requisitions(
        self, db_session: Session, test_requisition_link: RequisitionLink
    ) -> None:
        """Test that existing requisitions get status updated."""
        original_status = test_requisition_link.status
        new_status = "EX"

        requisitions = [{"id": test_requisition_link.id, "status": new_status}]

        result = upsert_requisitions(db_session, requisitions)
        db_session.commit()

        assert result == 1
        updated = db_session.get(RequisitionLink, test_requisition_link.id)
        assert updated is not None
        assert updated.status == new_status
        assert updated.status != original_status

    def test_upsert_skips_unknown_requisitions(self, db_session: Session) -> None:
        """Test that requisitions not in DB are skipped."""
        requisitions = [
            {"id": "unknown-req-1", "status": "LN"},
            {"id": "unknown-req-2", "status": "CR"},
        ]

        result = upsert_requisitions(db_session, requisitions)

        assert result == 0

    def test_upsert_mixed_known_and_unknown(
        self, db_session: Session, test_requisition_link: RequisitionLink
    ) -> None:
        """Test that only known requisitions are updated."""
        requisitions = [
            {"id": test_requisition_link.id, "status": "EX"},
            {"id": "unknown-req", "status": "LN"},
        ]

        result = upsert_requisitions(db_session, requisitions)
        db_session.commit()

        # Only one should be updated (the known one)
        assert result == 1
        updated = db_session.get(RequisitionLink, test_requisition_link.id)
        assert updated is not None
        assert updated.status == "EX"

    def test_upsert_logs_status_change(
        self, db_session: Session, test_requisition_link: RequisitionLink
    ) -> None:
        """Test that status changes are logged (coverage for logging branch)."""
        # Set initial status
        test_requisition_link.status = "CR"
        db_session.commit()

        # Update to different status
        requisitions = [{"id": test_requisition_link.id, "status": "LN"}]

        result = upsert_requisitions(db_session, requisitions)
        db_session.commit()

        assert result == 1
        updated = db_session.get(RequisitionLink, test_requisition_link.id)
        assert updated is not None
        assert updated.status == "LN"

    def test_upsert_uses_existing_status_if_not_provided(
        self, db_session: Session, test_requisition_link: RequisitionLink
    ) -> None:
        """Test that existing status is preserved if not in payload."""
        original_status = test_requisition_link.status

        # Payload without status field
        requisitions = [{"id": test_requisition_link.id}]

        result = upsert_requisitions(db_session, requisitions)
        db_session.commit()

        assert result == 1
        updated = db_session.get(RequisitionLink, test_requisition_link.id)
        assert updated is not None
        assert updated.status == original_status
