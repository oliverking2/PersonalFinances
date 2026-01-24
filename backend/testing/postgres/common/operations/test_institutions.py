"""Tests for institution operations."""

from sqlalchemy.orm import Session

from src.postgres.common.enums import Provider
from src.postgres.common.models import Institution
from src.postgres.common.operations.institutions import (
    create_institution,
    get_institution_by_id,
    list_institutions,
    upsert_institution,
)


class TestGetInstitutionById:
    """Tests for get_institution_by_id operation."""

    def test_returns_institution_when_found(
        self, db_session: Session, test_institution: Institution
    ) -> None:
        """Should return institution when it exists."""
        result = get_institution_by_id(db_session, test_institution.id)

        assert result is not None
        assert result.id == test_institution.id
        assert result.name == test_institution.name

    def test_returns_none_when_not_found(self, db_session: Session) -> None:
        """Should return None when institution doesn't exist."""
        result = get_institution_by_id(db_session, "NONEXISTENT_ID")

        assert result is None


class TestListInstitutions:
    """Tests for list_institutions operation."""

    def test_returns_all_institutions(
        self, db_session: Session, test_institution: Institution
    ) -> None:
        """Should return all institutions when no filters."""
        result = list_institutions(db_session)

        assert len(result) >= 1
        assert any(inst.id == test_institution.id for inst in result)

    def test_filters_by_provider(self, db_session: Session, test_institution: Institution) -> None:
        """Should filter by provider when specified."""
        result = list_institutions(db_session, provider=Provider.GOCARDLESS)

        assert all(inst.provider == Provider.GOCARDLESS.value for inst in result)

    def test_filters_by_country(self, db_session: Session, test_institution: Institution) -> None:
        """Should filter by country when specified."""
        result = list_institutions(db_session, country="GB")

        assert all("GB" in (inst.countries or []) for inst in result)

    def test_returns_empty_for_no_matches(self, db_session: Session) -> None:
        """Should return empty list when no institutions match."""
        result = list_institutions(db_session, country="XX")

        assert result == []


class TestCreateInstitution:
    """Tests for create_institution operation."""

    def test_creates_institution(self, db_session: Session) -> None:
        """Should create institution with all fields."""
        result = create_institution(
            db_session,
            institution_id="MONZO_MONZGB2L",
            provider=Provider.GOCARDLESS,
            name="Monzo",
            logo_url="https://cdn.nordigen.com/ais/MONZO_MONZGB2L.png",
            countries=["GB"],
        )
        db_session.commit()

        assert result.id == "MONZO_MONZGB2L"
        assert result.provider == Provider.GOCARDLESS.value
        assert result.name == "Monzo"
        assert result.logo_url == "https://cdn.nordigen.com/ais/MONZO_MONZGB2L.png"
        assert result.countries == ["GB"]

    def test_creates_institution_with_minimal_fields(self, db_session: Session) -> None:
        """Should create institution with only required fields."""
        result = create_institution(
            db_session,
            institution_id="MINIMAL_ID",
            provider=Provider.GOCARDLESS,
            name="Minimal Bank",
        )
        db_session.commit()

        assert result.id == "MINIMAL_ID"
        assert result.logo_url is None
        assert result.countries is None


class TestUpsertInstitution:
    """Tests for upsert_institution operation."""

    def test_creates_new_institution(self, db_session: Session) -> None:
        """Should create institution when it doesn't exist."""
        result = upsert_institution(
            db_session,
            institution_id="NEW_INST_ID",
            provider=Provider.GOCARDLESS,
            name="New Bank",
        )
        db_session.commit()

        assert result.id == "NEW_INST_ID"
        assert result.name == "New Bank"

    def test_updates_existing_institution(
        self, db_session: Session, test_institution: Institution
    ) -> None:
        """Should update institution when it exists."""
        result = upsert_institution(
            db_session,
            institution_id=test_institution.id,
            provider=Provider.GOCARDLESS,
            name="Updated Name",
            logo_url="https://new-logo.png",
        )
        db_session.commit()

        assert result.id == test_institution.id
        assert result.name == "Updated Name"
        assert result.logo_url == "https://new-logo.png"
