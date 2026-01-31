"""Tests for financial milestone operations."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from src.postgres.common.operations.financial_milestones import (
    check_and_update_achievements,
    create_milestone,
    delete_milestone,
    get_milestone_by_id,
    get_milestones_by_user_id,
    mark_milestone_achieved,
    update_milestone,
)


@pytest.fixture
def user_id() -> str:
    """Generate a test user ID."""
    return uuid4()


class TestCreateMilestone:
    """Tests for create_milestone."""

    def test_creates_milestone_with_required_fields(
        self, db_session: Session, user_id: str
    ) -> None:
        """Creates a milestone with name and target."""
        milestone = create_milestone(
            db_session,
            user_id,
            name="Emergency Fund",
            target_amount=Decimal("10000.00"),
        )

        assert milestone.id is not None
        assert milestone.user_id == user_id
        assert milestone.name == "Emergency Fund"
        assert milestone.target_amount == Decimal("10000.00")
        assert milestone.achieved is False
        assert milestone.achieved_at is None
        assert milestone.colour == "#f59e0b"  # Default amber

    def test_creates_milestone_with_all_fields(self, db_session: Session, user_id: str) -> None:
        """Creates a milestone with all optional fields."""
        target_date = datetime.now(UTC) + timedelta(days=365)

        milestone = create_milestone(
            db_session,
            user_id,
            name="First £100K",
            target_amount=Decimal("100000.00"),
            target_date=target_date,
            colour="#10b981",
            notes="The big one!",
        )

        assert milestone.name == "First £100K"
        assert milestone.target_amount == Decimal("100000.00")
        assert milestone.target_date.year == target_date.year
        assert milestone.colour == "#10b981"
        assert milestone.notes == "The big one!"


class TestGetMilestones:
    """Tests for milestone retrieval."""

    def test_get_by_id_returns_milestone(self, db_session: Session, user_id: str) -> None:
        """Returns milestone when it exists."""
        created = create_milestone(db_session, user_id, "Test", Decimal("1000.00"))

        result = get_milestone_by_id(db_session, created.id)

        assert result is not None
        assert result.id == created.id

    def test_get_by_id_returns_none_for_missing(self, db_session: Session) -> None:
        """Returns None for non-existent ID."""
        result = get_milestone_by_id(db_session, uuid4())
        assert result is None

    def test_get_by_user_id_returns_all(self, db_session: Session, user_id: str) -> None:
        """Returns all milestones for user ordered by target_amount."""
        create_milestone(db_session, user_id, "Big", Decimal("50000.00"))
        create_milestone(db_session, user_id, "Small", Decimal("1000.00"))
        create_milestone(db_session, user_id, "Medium", Decimal("10000.00"))

        results = get_milestones_by_user_id(db_session, user_id)

        assert len(results) == 3
        assert results[0].name == "Small"  # Ordered by target_amount
        assert results[1].name == "Medium"
        assert results[2].name == "Big"

    def test_get_by_user_id_filters_achieved(self, db_session: Session, user_id: str) -> None:
        """Can filter by achieved status."""
        m1 = create_milestone(db_session, user_id, "Achieved", Decimal("1000.00"))
        create_milestone(db_session, user_id, "Pending", Decimal("2000.00"))
        mark_milestone_achieved(db_session, m1.id)

        achieved = get_milestones_by_user_id(db_session, user_id, achieved_only=True)
        pending = get_milestones_by_user_id(db_session, user_id, pending_only=True)

        assert len(achieved) == 1
        assert achieved[0].name == "Achieved"
        assert len(pending) == 1
        assert pending[0].name == "Pending"


class TestUpdateMilestone:
    """Tests for update_milestone."""

    def test_updates_name(self, db_session: Session, user_id: str) -> None:
        """Updates milestone name."""
        milestone = create_milestone(db_session, user_id, "Old Name", Decimal("1000.00"))

        result = update_milestone(db_session, milestone.id, name="New Name")

        assert result is not None
        assert result.name == "New Name"

    def test_updates_target_amount(self, db_session: Session, user_id: str) -> None:
        """Updates target amount."""
        milestone = create_milestone(db_session, user_id, "Test", Decimal("1000.00"))

        result = update_milestone(db_session, milestone.id, target_amount=Decimal("2000.00"))

        assert result is not None
        assert result.target_amount == Decimal("2000.00")

    def test_clears_optional_field_with_none(self, db_session: Session, user_id: str) -> None:
        """Clears notes field when set to None."""
        milestone = create_milestone(
            db_session,
            user_id,
            "Test",
            Decimal("1000.00"),
            notes="Some notes",
        )

        result = update_milestone(db_session, milestone.id, notes=None)

        assert result is not None
        assert result.notes is None

    def test_returns_none_for_missing(self, db_session: Session) -> None:
        """Returns None when milestone doesn't exist."""
        result = update_milestone(db_session, uuid4(), name="New")
        assert result is None


class TestMarkMilestoneAchieved:
    """Tests for mark_milestone_achieved."""

    def test_marks_as_achieved(self, db_session: Session, user_id: str) -> None:
        """Marks milestone as achieved with timestamp."""
        milestone = create_milestone(db_session, user_id, "Test", Decimal("1000.00"))

        result = mark_milestone_achieved(db_session, milestone.id)

        assert result is not None
        assert result.achieved is True
        assert result.achieved_at is not None

    def test_uses_provided_timestamp(self, db_session: Session, user_id: str) -> None:
        """Uses provided achieved_at timestamp."""
        milestone = create_milestone(db_session, user_id, "Test", Decimal("1000.00"))
        custom_time = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)

        result = mark_milestone_achieved(db_session, milestone.id, achieved_at=custom_time)

        assert result is not None
        assert result.achieved_at == custom_time


class TestDeleteMilestone:
    """Tests for delete_milestone."""

    def test_deletes_milestone(self, db_session: Session, user_id: str) -> None:
        """Successfully deletes milestone."""
        milestone = create_milestone(db_session, user_id, "Test", Decimal("1000.00"))

        result = delete_milestone(db_session, milestone.id)

        assert result is True
        assert get_milestone_by_id(db_session, milestone.id) is None

    def test_returns_false_for_missing(self, db_session: Session) -> None:
        """Returns False when milestone doesn't exist."""
        result = delete_milestone(db_session, uuid4())
        assert result is False


class TestCheckAndUpdateAchievements:
    """Tests for check_and_update_achievements."""

    def test_marks_exceeded_milestones_as_achieved(self, db_session: Session, user_id: str) -> None:
        """Marks milestones where net worth exceeds target."""
        create_milestone(db_session, user_id, "Small", Decimal("1000.00"))
        create_milestone(db_session, user_id, "Medium", Decimal("5000.00"))
        create_milestone(db_session, user_id, "Big", Decimal("10000.00"))

        achieved = check_and_update_achievements(db_session, user_id, Decimal("6000.00"))

        assert len(achieved) == 2
        achieved_names = {m.name for m in achieved}
        assert achieved_names == {"Small", "Medium"}

    def test_ignores_already_achieved(self, db_session: Session, user_id: str) -> None:
        """Doesn't re-achieve already achieved milestones."""
        m1 = create_milestone(db_session, user_id, "Already Done", Decimal("1000.00"))
        mark_milestone_achieved(db_session, m1.id)

        achieved = check_and_update_achievements(db_session, user_id, Decimal("5000.00"))

        assert len(achieved) == 0

    def test_returns_empty_when_none_achieved(self, db_session: Session, user_id: str) -> None:
        """Returns empty list when net worth doesn't exceed any milestones."""
        create_milestone(db_session, user_id, "Big", Decimal("100000.00"))

        achieved = check_and_update_achievements(db_session, user_id, Decimal("5000.00"))

        assert len(achieved) == 0
