"""Tests for savings goal database operations."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.enums import (
    AccountStatus,
    AccountType,
    ConnectionStatus,
    GoalStatus,
    GoalTrackingMode,
    Provider,
)
from src.postgres.common.models import Account, Connection, Institution
from src.postgres.common.operations.goals import (
    ContributionNotAllowedError,
    cancel_goal,
    complete_goal,
    contribute_to_goal,
    create_goal,
    delete_goal,
    get_goal_by_id,
    get_goals_by_user_id,
    pause_goal,
    resume_goal,
    update_goal,
)


class TestGoalCRUD:
    """Tests for basic goal CRUD operations."""

    def test_create_goal(self, db_session: Session, test_user: User) -> None:
        """Should create a savings goal."""
        goal = create_goal(
            db_session,
            user_id=test_user.id,
            name="Emergency Fund",
            target_amount=Decimal("5000.00"),
        )
        db_session.commit()

        assert goal.id is not None
        assert goal.user_id == test_user.id
        assert goal.name == "Emergency Fund"
        assert goal.target_amount == Decimal("5000.00")
        assert goal.current_amount == Decimal("0")
        assert goal.currency == "GBP"
        assert goal.status == GoalStatus.ACTIVE.value

    def test_create_goal_with_initial_amount(self, db_session: Session, test_user: User) -> None:
        """Should create a goal with starting amount."""
        goal = create_goal(
            db_session,
            user_id=test_user.id,
            name="Vacation",
            target_amount=Decimal("3000.00"),
            current_amount=Decimal("500.00"),
        )
        db_session.commit()

        assert goal.current_amount == Decimal("500.00")

    def test_create_goal_with_deadline(self, db_session: Session, test_user: User) -> None:
        """Should create a goal with deadline."""
        deadline = datetime.now(UTC) + timedelta(days=180)
        goal = create_goal(
            db_session,
            user_id=test_user.id,
            name="Holiday",
            target_amount=Decimal("2000.00"),
            deadline=deadline,
        )
        db_session.commit()

        assert goal.deadline is not None

    def test_create_goal_truncates_name(self, db_session: Session, test_user: User) -> None:
        """Should truncate long goal names to 100 characters."""
        long_name = "x" * 150
        goal = create_goal(
            db_session,
            user_id=test_user.id,
            name=long_name,
            target_amount=Decimal("1000.00"),
        )
        db_session.commit()

        assert len(goal.name) == 100

    def test_get_goal_by_id(self, db_session: Session, test_user: User) -> None:
        """Should retrieve goal by ID."""
        goal = create_goal(
            db_session,
            user_id=test_user.id,
            name="Test",
            target_amount=Decimal("1000.00"),
        )
        db_session.commit()

        result = get_goal_by_id(db_session, goal.id)
        assert result is not None
        assert result.id == goal.id

    def test_get_goal_by_id_not_found(self, db_session: Session) -> None:
        """Should return None for non-existent goal."""
        result = get_goal_by_id(db_session, uuid4())
        assert result is None

    def test_get_goals_by_user_id(self, db_session: Session, test_user: User) -> None:
        """Should retrieve all active goals for a user."""
        create_goal(db_session, test_user.id, "Goal 1", Decimal("1000.00"))
        create_goal(db_session, test_user.id, "Goal 2", Decimal("2000.00"))
        db_session.commit()

        goals = get_goals_by_user_id(db_session, test_user.id)
        assert len(goals) == 2

    def test_get_goals_excludes_inactive(self, db_session: Session, test_user: User) -> None:
        """Should exclude completed and cancelled goals by default."""
        g1 = create_goal(db_session, test_user.id, "Active", Decimal("1000.00"))
        g2 = create_goal(db_session, test_user.id, "Completed", Decimal("1000.00"))
        complete_goal(db_session, g2.id)
        db_session.commit()

        goals = get_goals_by_user_id(db_session, test_user.id)
        assert len(goals) == 1
        assert goals[0].id == g1.id

    def test_get_goals_include_inactive(self, db_session: Session, test_user: User) -> None:
        """Should include all goals when requested."""
        create_goal(db_session, test_user.id, "Active", Decimal("1000.00"))
        g2 = create_goal(db_session, test_user.id, "Completed", Decimal("1000.00"))
        complete_goal(db_session, g2.id)
        db_session.commit()

        goals = get_goals_by_user_id(db_session, test_user.id, include_inactive=True)
        assert len(goals) == 2


class TestGoalContributions:
    """Tests for goal contribution operations."""

    def test_contribute_to_goal(self, db_session: Session, test_user: User) -> None:
        """Should add contribution to goal."""
        goal = create_goal(
            db_session,
            user_id=test_user.id,
            name="Test",
            target_amount=Decimal("1000.00"),
        )
        db_session.commit()

        result = contribute_to_goal(db_session, goal.id, Decimal("200.00"))
        db_session.commit()

        assert result is not None
        assert result.current_amount == Decimal("200.00")

    def test_contribute_auto_completes(self, db_session: Session, test_user: User) -> None:
        """Should auto-complete goal when target reached."""
        goal = create_goal(
            db_session,
            user_id=test_user.id,
            name="Test",
            target_amount=Decimal("100.00"),
            current_amount=Decimal("90.00"),
        )
        db_session.commit()

        result = contribute_to_goal(db_session, goal.id, Decimal("15.00"))
        db_session.commit()

        assert result is not None
        assert result.current_amount == Decimal("105.00")
        assert result.status == GoalStatus.COMPLETED.value

    def test_contribute_withdrawal(self, db_session: Session, test_user: User) -> None:
        """Should allow negative contributions (withdrawals)."""
        goal = create_goal(
            db_session,
            user_id=test_user.id,
            name="Test",
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("500.00"),
        )
        db_session.commit()

        result = contribute_to_goal(db_session, goal.id, Decimal("-100.00"))
        db_session.commit()

        assert result is not None
        assert result.current_amount == Decimal("400.00")


class TestGoalStatusOperations:
    """Tests for goal status change operations."""

    def test_complete_goal(self, db_session: Session, test_user: User) -> None:
        """Should mark goal as completed."""
        goal = create_goal(
            db_session,
            user_id=test_user.id,
            name="Test",
            target_amount=Decimal("1000.00"),
        )
        db_session.commit()

        result = complete_goal(db_session, goal.id)
        db_session.commit()

        assert result is not None
        assert result.status == GoalStatus.COMPLETED.value

    def test_pause_goal(self, db_session: Session, test_user: User) -> None:
        """Should pause a goal."""
        goal = create_goal(
            db_session,
            user_id=test_user.id,
            name="Test",
            target_amount=Decimal("1000.00"),
        )
        db_session.commit()

        result = pause_goal(db_session, goal.id)
        db_session.commit()

        assert result is not None
        assert result.status == GoalStatus.PAUSED.value

    def test_resume_goal(self, db_session: Session, test_user: User) -> None:
        """Should resume a paused goal."""
        goal = create_goal(
            db_session,
            user_id=test_user.id,
            name="Test",
            target_amount=Decimal("1000.00"),
        )
        pause_goal(db_session, goal.id)
        db_session.commit()

        result = resume_goal(db_session, goal.id)
        db_session.commit()

        assert result is not None
        assert result.status == GoalStatus.ACTIVE.value

    def test_cancel_goal(self, db_session: Session, test_user: User) -> None:
        """Should cancel a goal."""
        goal = create_goal(
            db_session,
            user_id=test_user.id,
            name="Test",
            target_amount=Decimal("1000.00"),
        )
        db_session.commit()

        result = cancel_goal(db_session, goal.id)
        db_session.commit()

        assert result is not None
        assert result.status == GoalStatus.CANCELLED.value


class TestGoalUpdate:
    """Tests for goal update operations."""

    def test_update_name(self, db_session: Session, test_user: User) -> None:
        """Should update goal name."""
        goal = create_goal(
            db_session,
            user_id=test_user.id,
            name="Original",
            target_amount=Decimal("1000.00"),
        )
        db_session.commit()

        result = update_goal(db_session, goal.id, name="Updated")
        db_session.commit()

        assert result is not None
        assert result.name == "Updated"

    def test_update_target_amount(self, db_session: Session, test_user: User) -> None:
        """Should update target amount."""
        goal = create_goal(
            db_session,
            user_id=test_user.id,
            name="Test",
            target_amount=Decimal("1000.00"),
        )
        db_session.commit()

        result = update_goal(db_session, goal.id, target_amount=Decimal("2000.00"))
        db_session.commit()

        assert result is not None
        assert result.target_amount == Decimal("2000.00")

    def test_update_clear_deadline(self, db_session: Session, test_user: User) -> None:
        """Should clear deadline."""
        deadline = datetime.now(UTC) + timedelta(days=180)
        goal = create_goal(
            db_session,
            user_id=test_user.id,
            name="Test",
            target_amount=Decimal("1000.00"),
            deadline=deadline,
        )
        db_session.commit()

        result = update_goal(db_session, goal.id, deadline=None)
        db_session.commit()

        assert result is not None
        assert result.deadline is None


class TestGoalDelete:
    """Tests for goal delete operations."""

    def test_delete_goal(self, db_session: Session, test_user: User) -> None:
        """Should delete a goal."""
        goal = create_goal(
            db_session,
            user_id=test_user.id,
            name="Test",
            target_amount=Decimal("1000.00"),
        )
        db_session.commit()

        result = delete_goal(db_session, goal.id)
        db_session.commit()

        assert result is True
        assert get_goal_by_id(db_session, goal.id) is None

    def test_delete_not_found(self, db_session: Session) -> None:
        """Should return False when deleting non-existent goal."""
        result = delete_goal(db_session, uuid4())
        assert result is False


@pytest.fixture
def test_institution(db_session: Session) -> Institution:
    """Create a test institution."""
    institution = Institution(
        id="TEST_BANK_GB",
        provider=Provider.GOCARDLESS.value,
        name="Test Bank",
        logo_url="https://example.com/logo.png",
        countries=["GB"],
    )
    db_session.add(institution)
    db_session.commit()
    return institution


@pytest.fixture
def test_connection(
    db_session: Session, test_user: User, test_institution: Institution
) -> Connection:
    """Create a test connection."""
    from datetime import datetime  # noqa: PLC0415

    connection = Connection(
        user_id=test_user.id,
        provider=Provider.GOCARDLESS.value,
        provider_id="test-req-id",
        institution_id=test_institution.id,
        friendly_name="Test Connection",
        status=ConnectionStatus.ACTIVE.value,
        created_at=datetime.now(),
    )
    db_session.add(connection)
    db_session.commit()
    return connection


@pytest.fixture
def test_account(db_session: Session, test_connection: Connection) -> Account:
    """Create a test account with balance."""
    account = Account(
        connection_id=test_connection.id,
        provider_id="test-gc-account-id",
        account_type=AccountType.BANK.value,
        status=AccountStatus.ACTIVE.value,
        name="Test Savings",
        display_name="My Savings",
        currency="GBP",
        balance_amount=Decimal("5000.00"),
        balance_currency="GBP",
    )
    db_session.add(account)
    db_session.commit()
    return account


class TestGoalTrackingModes:
    """Tests for goal tracking modes."""

    def test_create_manual_goal(self, db_session: Session, test_user: User) -> None:
        """Should create a manual tracking goal by default."""
        goal = create_goal(
            db_session,
            user_id=test_user.id,
            name="Manual Goal",
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("100.00"),
        )
        db_session.commit()

        assert goal.tracking_mode == GoalTrackingMode.MANUAL.value
        assert goal.current_amount == Decimal("100.00")
        assert goal.starting_balance is None
        assert goal.target_balance is None

    def test_create_balance_goal(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should create a balance tracking goal."""
        goal = create_goal(
            db_session,
            user_id=test_user.id,
            name="Balance Goal",
            target_amount=Decimal("10000.00"),
            account_id=test_account.id,
            tracking_mode=GoalTrackingMode.BALANCE,
        )
        db_session.commit()

        assert goal.tracking_mode == GoalTrackingMode.BALANCE.value
        assert goal.account_id == test_account.id
        # Starting balance not set for balance mode
        assert goal.starting_balance is None

    def test_create_delta_goal_snapshots_balance(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should snapshot account balance for delta tracking goal."""
        goal = create_goal(
            db_session,
            user_id=test_user.id,
            name="Delta Goal",
            target_amount=Decimal("2000.00"),
            account_id=test_account.id,
            tracking_mode=GoalTrackingMode.DELTA,
        )
        db_session.commit()

        assert goal.tracking_mode == GoalTrackingMode.DELTA.value
        assert goal.account_id == test_account.id
        # Starting balance should be captured from account
        assert goal.starting_balance == Decimal("5000.00")

    def test_create_target_balance_goal(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should create a target_balance tracking goal."""
        goal = create_goal(
            db_session,
            user_id=test_user.id,
            name="Target Balance Goal",
            target_amount=Decimal("10000.00"),
            account_id=test_account.id,
            tracking_mode=GoalTrackingMode.TARGET_BALANCE,
            target_balance=Decimal("10000.00"),
        )
        db_session.commit()

        assert goal.tracking_mode == GoalTrackingMode.TARGET_BALANCE.value
        assert goal.target_balance == Decimal("10000.00")

    def test_balance_mode_requires_account(self, db_session: Session, test_user: User) -> None:
        """Should raise error when balance mode lacks account."""
        with pytest.raises(ValueError, match=r"[Aa]ccount.*required"):
            create_goal(
                db_session,
                user_id=test_user.id,
                name="Missing Account",
                target_amount=Decimal("1000.00"),
                tracking_mode=GoalTrackingMode.BALANCE,
            )

    def test_delta_mode_requires_account(self, db_session: Session, test_user: User) -> None:
        """Should raise error when delta mode lacks account."""
        with pytest.raises(ValueError, match=r"[Aa]ccount.*required"):
            create_goal(
                db_session,
                user_id=test_user.id,
                name="Missing Account",
                target_amount=Decimal("1000.00"),
                tracking_mode=GoalTrackingMode.DELTA,
            )

    def test_target_balance_mode_requires_target(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should raise error when target_balance mode lacks target_balance field."""
        with pytest.raises(ValueError, match=r"[Tt]arget balance.*required"):
            create_goal(
                db_session,
                user_id=test_user.id,
                name="Missing Target",
                target_amount=Decimal("1000.00"),
                account_id=test_account.id,
                tracking_mode=GoalTrackingMode.TARGET_BALANCE,
            )

    def test_contribute_to_manual_goal(self, db_session: Session, test_user: User) -> None:
        """Should allow contributions to manual tracking goals."""
        goal = create_goal(
            db_session,
            user_id=test_user.id,
            name="Manual Goal",
            target_amount=Decimal("1000.00"),
            tracking_mode=GoalTrackingMode.MANUAL,
        )
        db_session.commit()

        result = contribute_to_goal(db_session, goal.id, Decimal("200.00"))
        db_session.commit()

        assert result is not None
        assert result.current_amount == Decimal("200.00")

    def test_contribute_to_balance_goal_blocked(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should block contributions to balance tracking goals."""
        goal = create_goal(
            db_session,
            user_id=test_user.id,
            name="Balance Goal",
            target_amount=Decimal("10000.00"),
            account_id=test_account.id,
            tracking_mode=GoalTrackingMode.BALANCE,
        )
        db_session.commit()

        with pytest.raises(ContributionNotAllowedError, match="manual"):
            contribute_to_goal(db_session, goal.id, Decimal("200.00"))

    def test_contribute_to_delta_goal_blocked(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should block contributions to delta tracking goals."""
        goal = create_goal(
            db_session,
            user_id=test_user.id,
            name="Delta Goal",
            target_amount=Decimal("2000.00"),
            account_id=test_account.id,
            tracking_mode=GoalTrackingMode.DELTA,
        )
        db_session.commit()

        with pytest.raises(ContributionNotAllowedError, match="manual"):
            contribute_to_goal(db_session, goal.id, Decimal("200.00"))

    def test_tracking_mode_enum_property(self, db_session: Session, test_user: User) -> None:
        """Should provide tracking_mode_enum property."""
        goal = create_goal(
            db_session,
            user_id=test_user.id,
            name="Test Goal",
            target_amount=Decimal("1000.00"),
            tracking_mode=GoalTrackingMode.MANUAL,
        )
        db_session.commit()

        assert goal.tracking_mode_enum == GoalTrackingMode.MANUAL
