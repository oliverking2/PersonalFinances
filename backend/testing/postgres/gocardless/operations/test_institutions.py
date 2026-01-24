"""Tests for GoCardless institution operations."""

from sqlalchemy.orm import Session

from src.postgres.gocardless.models import GoCardlessInstitution
from src.postgres.gocardless.operations.institutions import upsert_institutions


class TestUpsertInstitutions:
    """Tests for upsert_institutions operation."""

    def test_creates_new_institutions(self, db_session: Session) -> None:
        """Should create new institution records from API response."""
        institutions = [
            {
                "id": "CHASE_CHASGB2L",
                "name": "Chase UK",
                "bic": "CHASGB2L",
                "logo": "https://cdn.nordigen.com/ais/CHASE_CHASGB2L.png",
                "countries": ["GB"],
            },
            {
                "id": "NATIONWIDE_NAIAGB21",
                "name": "Nationwide Building Society",
                "bic": "NAIAGB21",
                "logo": "https://cdn.nordigen.com/ais/NATIONWIDE_NAIAGB21.png",
                "countries": ["GB"],
            },
        ]

        result = upsert_institutions(db_session, institutions)
        db_session.commit()

        assert result == 2

        # Verify institutions were created
        all_institutions = db_session.query(GoCardlessInstitution).all()
        assert len(all_institutions) == 2

        chase = db_session.get(GoCardlessInstitution, "CHASE_CHASGB2L")
        assert chase is not None
        assert chase.name == "Chase UK"
        assert chase.bic == "CHASGB2L"
        assert chase.logo == "https://cdn.nordigen.com/ais/CHASE_CHASGB2L.png"
        assert chase.countries == ["GB"]

    def test_updates_existing_institutions(self, db_session: Session) -> None:
        """Should update existing institution when same ID exists."""
        # Create initial institution
        initial = GoCardlessInstitution(
            id="CHASE_CHASGB2L",
            name="Chase",
            bic="OLD_BIC",
            logo="https://old-logo.png",
            countries=["GB"],
        )
        db_session.add(initial)
        db_session.commit()

        # Upsert with updated data
        institutions = [
            {
                "id": "CHASE_CHASGB2L",
                "name": "Chase UK",
                "bic": "CHASGB2L",
                "logo": "https://cdn.nordigen.com/ais/CHASE_CHASGB2L.png",
                "countries": ["GB", "IE"],
            },
        ]

        result = upsert_institutions(db_session, institutions)
        db_session.commit()

        assert result == 1

        # Verify institution was updated (not duplicated)
        all_institutions = db_session.query(GoCardlessInstitution).all()
        assert len(all_institutions) == 1

        chase = db_session.get(GoCardlessInstitution, "CHASE_CHASGB2L")
        assert chase is not None
        assert chase.name == "Chase UK"
        assert chase.bic == "CHASGB2L"
        assert chase.logo == "https://cdn.nordigen.com/ais/CHASE_CHASGB2L.png"
        assert chase.countries == ["GB", "IE"]

    def test_handles_empty_list(self, db_session: Session) -> None:
        """Should handle empty institutions list gracefully."""
        result = upsert_institutions(db_session, [])
        assert result == 0

    def test_handles_missing_optional_fields(self, db_session: Session) -> None:
        """Should handle institutions with missing optional fields."""
        institutions = [
            {
                "id": "TEST_BANK",
                "name": "Test Bank",
                # No bic, logo, or countries
            },
        ]

        result = upsert_institutions(db_session, institutions)
        db_session.commit()

        assert result == 1

        inst = db_session.get(GoCardlessInstitution, "TEST_BANK")
        assert inst is not None
        assert inst.name == "Test Bank"
        assert inst.bic is None
        assert inst.logo is None
        assert inst.countries is None

    def test_handles_mixed_create_and_update(self, db_session: Session) -> None:
        """Should handle mix of new and existing institutions."""
        # Create one existing institution
        existing = GoCardlessInstitution(
            id="EXISTING_BANK",
            name="Old Name",
            bic=None,
            logo=None,
            countries=None,
        )
        db_session.add(existing)
        db_session.commit()

        # Upsert with one existing and one new
        institutions = [
            {
                "id": "EXISTING_BANK",
                "name": "Updated Name",
                "countries": ["GB"],
            },
            {
                "id": "NEW_BANK",
                "name": "New Bank",
                "countries": ["GB"],
            },
        ]

        result = upsert_institutions(db_session, institutions)
        db_session.commit()

        assert result == 2

        all_institutions = db_session.query(GoCardlessInstitution).all()
        assert len(all_institutions) == 2

        updated = db_session.get(GoCardlessInstitution, "EXISTING_BANK")
        assert updated is not None
        assert updated.name == "Updated Name"

        new = db_session.get(GoCardlessInstitution, "NEW_BANK")
        assert new is not None
        assert new.name == "New Bank"
