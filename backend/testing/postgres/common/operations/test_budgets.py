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
    get_period_date_range,
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

    def test_weekly_period_key(self) -> None:
        """Should generate weekly period key in YYYY-Wxx format."""
        key = get_current_period_key(BudgetPeriod.WEEKLY)
        # Should be in format "YYYY-Wxx" (e.g., "2026-W05")
        assert len(key) == 8
        assert key[4] == "-"
        assert key[5] == "W"

    def test_quarterly_period_key(self) -> None:
        """Should generate quarterly period key in YYYY-Qx format."""
        key = get_current_period_key(BudgetPeriod.QUARTERLY)
        # Should be in format "YYYY-Qx" (e.g., "2026-Q1")
        assert len(key) == 7
        assert key[4] == "-"
        assert key[5] == "Q"
        assert key[6] in "1234"

    def test_annual_period_key(self) -> None:
        """Should generate annual period key in YYYY format."""
        key = get_current_period_key(BudgetPeriod.ANNUAL)
        # Should be in format "YYYY" (e.g., "2026")
        assert len(key) == 4
        assert key.isdigit()


class TestPeriodDateRange:
    """Tests for period date range calculation."""

    def test_weekly_range_starts_monday(self) -> None:
        """Should return weekly range starting from Monday."""
        start, end = get_period_date_range(BudgetPeriod.WEEKLY)

        # Start should be Monday (weekday 0)
        assert start.weekday() == 0
        # End should be Sunday (weekday 6)
        assert end.weekday() == 6
        # Start should be at midnight
        assert start.hour == 0
        assert start.minute == 0
        assert start.second == 0
        # End should be at 23:59:59
        assert end.hour == 23
        assert end.minute == 59
        assert end.second == 59

    def test_monthly_range_covers_full_month(self) -> None:
        """Should return monthly range from 1st to last day of month."""
        start, end = get_period_date_range(BudgetPeriod.MONTHLY)

        # Start should be 1st of month
        assert start.day == 1
        assert start.hour == 0
        # End should be at 23:59:59
        assert end.hour == 23
        assert end.minute == 59
        assert end.second == 59
        # End should be same month as start
        assert end.month == start.month

    def test_quarterly_range_covers_three_months(self) -> None:
        """Should return quarterly range covering 3 calendar months."""
        start, end = get_period_date_range(BudgetPeriod.QUARTERLY)

        # Start should be 1st of a quarter month (1, 4, 7, or 10)
        assert start.day == 1
        assert start.month in [1, 4, 7, 10]
        # End should be at 23:59:59
        assert end.hour == 23
        assert end.minute == 59
        # End month should be start month + 2 (unless wrapping year)
        expected_end_month = (start.month + 2) % 12 or 12
        assert end.month == expected_end_month

    def test_annual_range_covers_full_year(self) -> None:
        """Should return annual range from Jan 1 to Dec 31."""
        start, end = get_period_date_range(BudgetPeriod.ANNUAL)

        # Start should be January 1st
        assert start.month == 1
        assert start.day == 1
        assert start.hour == 0
        # End should be December 31st
        assert end.month == 12
        assert end.day == 31
        assert end.hour == 23
        assert end.minute == 59
        # Same year
        assert start.year == end.year


class TestBudgetWithPeriod:
    """Tests for budget operations with period field."""

    def test_create_budget_with_weekly_period(self, db_session: Session, test_user: User) -> None:
        """Should create a budget with weekly period."""
        tag = Tag(user_id=test_user.id, name="Coffee", colour="#8B4513")
        db_session.add(tag)
        db_session.commit()

        budget = create_budget(
            db_session,
            user_id=test_user.id,
            tag_id=tag.id,
            amount=Decimal("50.00"),
            period=BudgetPeriod.WEEKLY,
        )
        db_session.commit()

        assert budget.period == BudgetPeriod.WEEKLY.value

    def test_create_budget_with_quarterly_period(
        self, db_session: Session, test_user: User
    ) -> None:
        """Should create a budget with quarterly period."""
        tag = Tag(user_id=test_user.id, name="Insurance", colour="#4169E1")
        db_session.add(tag)
        db_session.commit()

        budget = create_budget(
            db_session,
            user_id=test_user.id,
            tag_id=tag.id,
            amount=Decimal("300.00"),
            period=BudgetPeriod.QUARTERLY,
        )
        db_session.commit()

        assert budget.period == BudgetPeriod.QUARTERLY.value

    def test_create_budget_with_annual_period(self, db_session: Session, test_user: User) -> None:
        """Should create a budget with annual period."""
        tag = Tag(user_id=test_user.id, name="Holiday", colour="#FF6347")
        db_session.add(tag)
        db_session.commit()

        budget = create_budget(
            db_session,
            user_id=test_user.id,
            tag_id=tag.id,
            amount=Decimal("3000.00"),
            period=BudgetPeriod.ANNUAL,
        )
        db_session.commit()

        assert budget.period == BudgetPeriod.ANNUAL.value

    def test_update_budget_period(self, db_session: Session, test_user: User) -> None:
        """Should update budget period."""
        tag = Tag(user_id=test_user.id, name="Test", colour="#000000")
        db_session.add(tag)
        db_session.commit()

        budget = create_budget(
            db_session,
            user_id=test_user.id,
            tag_id=tag.id,
            amount=Decimal("500.00"),
            period=BudgetPeriod.MONTHLY,
        )
        db_session.commit()

        result = update_budget(db_session, budget.id, period=BudgetPeriod.WEEKLY)
        db_session.commit()

        assert result is not None
        assert result.period == BudgetPeriod.WEEKLY.value
