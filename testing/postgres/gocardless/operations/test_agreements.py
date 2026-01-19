"""Tests for GoCardless agreements database operations."""

from datetime import datetime

from sqlalchemy.orm import Session

from src.postgres.gocardless.models import EndUserAgreement
from src.postgres.gocardless.operations.agreements import (
    add_agreement,
    upsert_agreement,
)


def build_agreement_data(
    agreement_id: str = "test-agreement-id",
    institution_id: str = "CHASE_CHASGB2L",
    accepted: datetime | None = None,
    reconfirmation: bool = False,
) -> dict:
    """Build mock agreement data for testing."""
    return {
        "id": agreement_id,
        "created": datetime(2024, 1, 1, 12, 0, 0),
        "institution_id": institution_id,
        "max_historical_days": 90,
        "access_valid_for_days": 90,
        "access_scope": "balances,transactions",
        "accepted": accepted,
        "reconfirmation": reconfirmation,
    }


class TestAddAgreement:
    """Tests for add_agreement function."""

    def test_add_agreement_success(self, db_session: Session) -> None:
        """Test successful agreement creation."""
        data = build_agreement_data(agreement_id="new-agreement")

        add_agreement(db_session, data)

        stored = db_session.get(EndUserAgreement, "new-agreement")
        assert stored is not None
        assert stored.institution_id == "CHASE_CHASGB2L"
        assert stored.max_historical_days == 90

    def test_add_agreement_with_accepted(self, db_session: Session) -> None:
        """Test agreement creation with accepted date."""
        accepted_time = datetime(2024, 1, 15, 14, 30, 0)
        data = build_agreement_data(agreement_id="accepted-agreement", accepted=accepted_time)

        add_agreement(db_session, data)

        stored = db_session.get(EndUserAgreement, "accepted-agreement")
        assert stored is not None
        assert stored.accepted == accepted_time


class TestUpsertAgreement:
    """Tests for upsert_agreement function."""

    def test_upsert_creates_new_agreement(self, db_session: Session) -> None:
        """Test that new agreement is created if not exists."""
        data = build_agreement_data(agreement_id="upsert-new")

        upsert_agreement(db_session, data)

        stored = db_session.get(EndUserAgreement, "upsert-new")
        assert stored is not None
        assert stored.institution_id == "CHASE_CHASGB2L"

    def test_upsert_updates_existing_agreement(self, db_session: Session) -> None:
        """Test that existing agreement is updated."""
        # Create initial agreement
        initial_data = build_agreement_data(agreement_id="upsert-existing", reconfirmation=False)
        add_agreement(db_session, initial_data)

        # Update with new data
        new_accepted = datetime(2024, 2, 1, 10, 0, 0)
        updated_data = build_agreement_data(
            agreement_id="upsert-existing",
            accepted=new_accepted,
            reconfirmation=True,
        )

        upsert_agreement(db_session, updated_data)

        stored = db_session.get(EndUserAgreement, "upsert-existing")
        assert stored is not None
        assert stored.accepted == new_accepted
        assert stored.reconfirmation is True
        # Original values should remain unchanged
        assert stored.max_historical_days == 90
