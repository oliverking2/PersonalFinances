"""Tests for budget database operations."""

from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.enums import BudgetPeriod
from src.postgres.common.models import Tag
from src.postgres.common.operations.budgets import (
    create_budget,
    delete_budget,
    get_budget_by_id,
    get_budget_by_tag,
    get_budgets_by_user_id,
    get_current_period_key,
    update_budget,
)


class TestBudgetCRUD:
    """Tests for basic budget CRUD operations."""

    def test_create_budget(self, db_session: Session, test_user: User) -> None:
        """Should create a budget."""
        tag = Tag(user_id=test_user.id, name="Groceries", colour="#10b981")
        db_session.add(tag)
        db_session.commit()

        budget = create_budget(
            db_session,
            user_id=test_user.id,
            tag_id=tag.id,
            amount=Decimal("500.00"),
        )
        db_session.commit()

        assert budget.id is not None
        assert budget.user_id == test_user.id
        assert budget.tag_id == tag.id
        assert budget.amount == Decimal("500.00")
        assert budget.currency == "GBP"
        assert budget.period == BudgetPeriod.MONTHLY.value
        assert budget.warning_threshold == Decimal("0.80")
        assert budget.enabled is True

    def test_create_budget_with_custom_threshold(
        self, db_session: Session, test_user: User
    ) -> None:
        """Should create a budget with custom warning threshold."""
        tag = Tag(user_id=test_user.id, name="Entertainment", colour="#6366f1")
        db_session.add(tag)
        db_session.commit()

        budget = create_budget(
            db_session,
            user_id=test_user.id,
            tag_id=tag.id,
            amount=Decimal("100.00"),
            warning_threshold=Decimal("0.90"),
        )
        db_session.commit()

        assert budget.warning_threshold == Decimal("0.90")

    def test_get_budget_by_id(self, db_session: Session, test_user: User) -> None:
        """Should retrieve budget by ID."""
        tag = Tag(user_id=test_user.id, name="Test", colour="#000000")
        db_session.add(tag)
        db_session.commit()

        budget = create_budget(
            db_session,
            user_id=test_user.id,
            tag_id=tag.id,
            amount=Decimal("200.00"),
        )
        db_session.commit()

        result = get_budget_by_id(db_session, budget.id)
        assert result is not None
        assert result.id == budget.id

    def test_get_budget_by_id_not_found(self, db_session: Session) -> None:
        """Should return None for non-existent budget."""
        result = get_budget_by_id(db_session, uuid4())
        assert result is None

    def test_get_budget_by_tag(self, db_session: Session, test_user: User) -> None:
        """Should retrieve budget by user and tag."""
        tag = Tag(user_id=test_user.id, name="Test", colour="#000000")
        db_session.add(tag)
        db_session.commit()

        budget = create_budget(
            db_session,
            user_id=test_user.id,
            tag_id=tag.id,
            amount=Decimal("300.00"),
        )
        db_session.commit()

        result = get_budget_by_tag(db_session, test_user.id, tag.id)
        assert result is not None
        assert result.id == budget.id

    def test_get_budgets_by_user_id(self, db_session: Session, test_user: User) -> None:
        """Should retrieve all budgets for a user."""
        tag1 = Tag(user_id=test_user.id, name="Food", colour="#10b981")
        tag2 = Tag(user_id=test_user.id, name="Transport", colour="#6366f1")
        db_session.add_all([tag1, tag2])
        db_session.commit()

        create_budget(db_session, test_user.id, tag1.id, Decimal("500.00"))
        create_budget(db_session, test_user.id, tag2.id, Decimal("200.00"))
        db_session.commit()

        budgets = get_budgets_by_user_id(db_session, test_user.id)
        assert len(budgets) == 2

    def test_get_budgets_enabled_only(self, db_session: Session, test_user: User) -> None:
        """Should filter to only enabled budgets."""
        tag1 = Tag(user_id=test_user.id, name="Active", colour="#10b981")
        tag2 = Tag(user_id=test_user.id, name="Disabled", colour="#6366f1")
        db_session.add_all([tag1, tag2])
        db_session.commit()

        create_budget(db_session, test_user.id, tag1.id, Decimal("500.00"), enabled=True)
        create_budget(db_session, test_user.id, tag2.id, Decimal("200.00"), enabled=False)
        db_session.commit()

        budgets = get_budgets_by_user_id(db_session, test_user.id, enabled_only=True)
        assert len(budgets) == 1
        assert budgets[0].tag_id == tag1.id


class TestBudgetUpdate:
    """Tests for budget update operations."""

    def test_update_amount(self, db_session: Session, test_user: User) -> None:
        """Should update budget amount."""
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

        result = update_budget(db_session, budget.id, amount=Decimal("600.00"))
        db_session.commit()

        assert result is not None
        assert result.amount == Decimal("600.00")

    def test_update_enabled(self, db_session: Session, test_user: User) -> None:
        """Should update budget enabled state."""
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

        result = update_budget(db_session, budget.id, enabled=False)
        db_session.commit()

        assert result is not None
        assert result.enabled is False

    def test_update_not_found(self, db_session: Session) -> None:
        """Should return None when updating non-existent budget."""
        result = update_budget(db_session, uuid4(), amount=Decimal("100.00"))
        assert result is None


class TestBudgetDelete:
    """Tests for budget delete operations."""

    def test_delete_budget(self, db_session: Session, test_user: User) -> None:
        """Should delete a budget."""
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

        result = delete_budget(db_session, budget.id)
        db_session.commit()

        assert result is True
        assert get_budget_by_id(db_session, budget.id) is None

    def test_delete_not_found(self, db_session: Session) -> None:
        """Should return False when deleting non-existent budget."""
        result = delete_budget(db_session, uuid4())
        assert result is False


class TestPeriodKey:
    """Tests for period key generation."""

    def test_monthly_period_key(self) -> None:
        """Should generate monthly period key in YYYY-MM format."""
        key = get_current_period_key(BudgetPeriod.MONTHLY)
        # Should be in format "YYYY-MM"
        assert len(key) == 7
        assert key[4] == "-"
