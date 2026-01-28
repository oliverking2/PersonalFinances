"""Tests for spending alert database operations."""

from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.enums import AlertStatus, AlertType
from src.postgres.common.models import Tag
from src.postgres.common.operations.alerts import (
    acknowledge_alert,
    acknowledge_all_alerts,
    create_alert,
    delete_alert,
    get_alert_by_id,
    get_alerts_by_user_id,
    get_pending_alerts_count,
)
from src.postgres.common.operations.budgets import create_budget


class TestAlertCRUD:
    """Tests for basic alert CRUD operations."""

    def test_create_alert(self, db_session: Session, test_user: User) -> None:
        """Should create a spending alert."""
        tag = Tag(user_id=test_user.id, name="Test", colour="#000000")
        db_session.add(tag)
        db_session.commit()

        budget = create_budget(
            db_session,
            user_id=test_user.id,
            tag_id=tag.id,
            amount=Decimal("500.00"),
        )
        db_session.commit()

        alert = create_alert(
            db_session,
            user_id=test_user.id,
            budget_id=budget.id,
            alert_type=AlertType.BUDGET_WARNING,
            period_key="2026-01",
            budget_amount=Decimal("500.00"),
            spent_amount=Decimal("420.00"),
            message="Approaching budget limit",
        )
        db_session.commit()

        assert alert is not None
        assert alert.user_id == test_user.id
        assert alert.budget_id == budget.id
        assert alert.alert_type == AlertType.BUDGET_WARNING.value
        assert alert.status == AlertStatus.PENDING.value

    def test_create_alert_deduplication(self, db_session: Session, test_user: User) -> None:
        """Should not create duplicate alerts for same budget/type/period."""
        tag = Tag(user_id=test_user.id, name="Test", colour="#000000")
        db_session.add(tag)
        db_session.commit()

        budget = create_budget(
            db_session,
            user_id=test_user.id,
            tag_id=tag.id,
            amount=Decimal("500.00"),
        )
        db_session.commit()

        alert1 = create_alert(
            db_session,
            user_id=test_user.id,
            budget_id=budget.id,
            alert_type=AlertType.BUDGET_WARNING,
            period_key="2026-01",
            budget_amount=Decimal("500.00"),
            spent_amount=Decimal("420.00"),
        )
        db_session.commit()

        # Try to create duplicate
        alert2 = create_alert(
            db_session,
            user_id=test_user.id,
            budget_id=budget.id,
            alert_type=AlertType.BUDGET_WARNING,
            period_key="2026-01",
            budget_amount=Decimal("500.00"),
            spent_amount=Decimal("450.00"),
        )
        db_session.commit()

        assert alert1 is not None
        assert alert2 is None  # Duplicate should not be created

    def test_create_different_type_same_period(self, db_session: Session, test_user: User) -> None:
        """Should allow different alert types for same budget/period."""
        tag = Tag(user_id=test_user.id, name="Test", colour="#000000")
        db_session.add(tag)
        db_session.commit()

        budget = create_budget(
            db_session,
            user_id=test_user.id,
            tag_id=tag.id,
            amount=Decimal("500.00"),
        )
        db_session.commit()

        alert1 = create_alert(
            db_session,
            user_id=test_user.id,
            budget_id=budget.id,
            alert_type=AlertType.BUDGET_WARNING,
            period_key="2026-01",
            budget_amount=Decimal("500.00"),
            spent_amount=Decimal("420.00"),
        )
        alert2 = create_alert(
            db_session,
            user_id=test_user.id,
            budget_id=budget.id,
            alert_type=AlertType.BUDGET_EXCEEDED,
            period_key="2026-01",
            budget_amount=Decimal("500.00"),
            spent_amount=Decimal("520.00"),
        )
        db_session.commit()

        assert alert1 is not None
        assert alert2 is not None

    def test_get_alert_by_id(self, db_session: Session, test_user: User) -> None:
        """Should retrieve alert by ID."""
        tag = Tag(user_id=test_user.id, name="Test", colour="#000000")
        db_session.add(tag)
        db_session.commit()

        budget = create_budget(db_session, test_user.id, tag.id, Decimal("500.00"))
        db_session.commit()

        alert = create_alert(
            db_session,
            user_id=test_user.id,
            budget_id=budget.id,
            alert_type=AlertType.BUDGET_WARNING,
            period_key="2026-01",
            budget_amount=Decimal("500.00"),
            spent_amount=Decimal("420.00"),
        )
        db_session.commit()

        result = get_alert_by_id(db_session, alert.id)
        assert result is not None
        assert result.id == alert.id

    def test_get_alert_by_id_not_found(self, db_session: Session) -> None:
        """Should return None for non-existent alert."""
        result = get_alert_by_id(db_session, uuid4())
        assert result is None

    def test_get_alerts_by_user_id(self, db_session: Session, test_user: User) -> None:
        """Should retrieve all alerts for a user."""
        tag = Tag(user_id=test_user.id, name="Test", colour="#000000")
        db_session.add(tag)
        db_session.commit()

        budget = create_budget(db_session, test_user.id, tag.id, Decimal("500.00"))
        db_session.commit()

        create_alert(
            db_session,
            test_user.id,
            budget.id,
            AlertType.BUDGET_WARNING,
            "2026-01",
            Decimal("500.00"),
            Decimal("420.00"),
        )
        create_alert(
            db_session,
            test_user.id,
            budget.id,
            AlertType.BUDGET_EXCEEDED,
            "2026-01",
            Decimal("500.00"),
            Decimal("520.00"),
        )
        db_session.commit()

        alerts = get_alerts_by_user_id(db_session, test_user.id)
        assert len(alerts) == 2


class TestAlertAcknowledge:
    """Tests for alert acknowledgement operations."""

    def test_acknowledge_alert(self, db_session: Session, test_user: User) -> None:
        """Should acknowledge an alert."""
        tag = Tag(user_id=test_user.id, name="Test", colour="#000000")
        db_session.add(tag)
        db_session.commit()

        budget = create_budget(db_session, test_user.id, tag.id, Decimal("500.00"))
        db_session.commit()

        alert = create_alert(
            db_session,
            test_user.id,
            budget.id,
            AlertType.BUDGET_WARNING,
            "2026-01",
            Decimal("500.00"),
            Decimal("420.00"),
        )
        db_session.commit()

        result = acknowledge_alert(db_session, alert.id)
        db_session.commit()

        assert result is not None
        assert result.status == AlertStatus.ACKNOWLEDGED.value
        assert result.acknowledged_at is not None

    def test_acknowledge_all_alerts(self, db_session: Session, test_user: User) -> None:
        """Should acknowledge all pending alerts for a user."""
        tag = Tag(user_id=test_user.id, name="Test", colour="#000000")
        db_session.add(tag)
        db_session.commit()

        budget = create_budget(db_session, test_user.id, tag.id, Decimal("500.00"))
        db_session.commit()

        create_alert(
            db_session,
            test_user.id,
            budget.id,
            AlertType.BUDGET_WARNING,
            "2026-01",
            Decimal("500.00"),
            Decimal("420.00"),
        )
        create_alert(
            db_session,
            test_user.id,
            budget.id,
            AlertType.BUDGET_EXCEEDED,
            "2026-01",
            Decimal("500.00"),
            Decimal("520.00"),
        )
        db_session.commit()

        count = acknowledge_all_alerts(db_session, test_user.id)
        db_session.commit()

        assert count == 2

        # Verify all are acknowledged
        alerts = get_alerts_by_user_id(db_session, test_user.id)
        assert all(a.status == AlertStatus.ACKNOWLEDGED.value for a in alerts)


class TestAlertCount:
    """Tests for alert count operations."""

    def test_get_pending_alerts_count(self, db_session: Session, test_user: User) -> None:
        """Should count pending alerts."""
        tag = Tag(user_id=test_user.id, name="Test", colour="#000000")
        db_session.add(tag)
        db_session.commit()

        budget = create_budget(db_session, test_user.id, tag.id, Decimal("500.00"))
        db_session.commit()

        alert1 = create_alert(
            db_session,
            test_user.id,
            budget.id,
            AlertType.BUDGET_WARNING,
            "2026-01",
            Decimal("500.00"),
            Decimal("420.00"),
        )
        create_alert(
            db_session,
            test_user.id,
            budget.id,
            AlertType.BUDGET_EXCEEDED,
            "2026-01",
            Decimal("500.00"),
            Decimal("520.00"),
        )
        db_session.commit()

        count = get_pending_alerts_count(db_session, test_user.id)
        assert count == 2

        # Acknowledge one
        acknowledge_alert(db_session, alert1.id)
        db_session.commit()

        count = get_pending_alerts_count(db_session, test_user.id)
        assert count == 1


class TestAlertDelete:
    """Tests for alert delete operations."""

    def test_delete_alert(self, db_session: Session, test_user: User) -> None:
        """Should delete an alert."""
        tag = Tag(user_id=test_user.id, name="Test", colour="#000000")
        db_session.add(tag)
        db_session.commit()

        budget = create_budget(db_session, test_user.id, tag.id, Decimal("500.00"))
        db_session.commit()

        alert = create_alert(
            db_session,
            test_user.id,
            budget.id,
            AlertType.BUDGET_WARNING,
            "2026-01",
            Decimal("500.00"),
            Decimal("420.00"),
        )
        db_session.commit()

        result = delete_alert(db_session, alert.id)
        db_session.commit()

        assert result is True
        assert get_alert_by_id(db_session, alert.id) is None

    def test_delete_not_found(self, db_session: Session) -> None:
        """Should return False when deleting non-existent alert."""
        result = delete_alert(db_session, uuid4())
        assert result is False
