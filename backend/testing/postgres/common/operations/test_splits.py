"""Tests for transaction split database operations."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.models import Account, Transaction, TransactionSplit
from src.postgres.common.operations.splits import (
    SplitValidationError,
    clear_transaction_splits,
    get_splits_with_tags,
    get_transaction_splits,
    set_transaction_splits,
    validate_splits,
)
from src.postgres.common.operations.tags import create_tag


class TestValidateSplits:
    """Tests for split validation logic."""

    def test_validate_splits_success(self) -> None:
        """Should pass when splits sum to transaction amount."""
        tag_id1, tag_id2 = uuid4(), uuid4()
        validate_splits(
            Decimal("-100.00"),
            [(tag_id1, Decimal("60.00")), (tag_id2, Decimal("40.00"))],
        )
        # No exception raised

    def test_validate_splits_empty(self) -> None:
        """Should fail when no splits provided."""
        with pytest.raises(SplitValidationError, match="At least one split"):
            validate_splits(Decimal("-100.00"), [])

    def test_validate_splits_duplicate_tags(self) -> None:
        """Should fail when same tag appears twice."""
        tag_id = uuid4()
        with pytest.raises(SplitValidationError, match="Duplicate tags"):
            validate_splits(
                Decimal("-100.00"),
                [(tag_id, Decimal("60.00")), (tag_id, Decimal("40.00"))],
            )

    def test_validate_splits_negative_amount(self) -> None:
        """Should fail when split amount is negative."""
        with pytest.raises(SplitValidationError, match="must be positive"):
            validate_splits(
                Decimal("-100.00"),
                [(uuid4(), Decimal("-60.00"))],
            )

    def test_validate_splits_zero_amount(self) -> None:
        """Should fail when split amount is zero."""
        with pytest.raises(SplitValidationError, match="must be positive"):
            validate_splits(
                Decimal("-100.00"),
                [(uuid4(), Decimal("0.00"))],
            )

    def test_validate_splits_sum_mismatch(self) -> None:
        """Should fail when splits don't sum to transaction amount."""
        with pytest.raises(SplitValidationError, match="must equal transaction amount"):
            validate_splits(
                Decimal("-100.00"),
                [(uuid4(), Decimal("50.00")), (uuid4(), Decimal("30.00"))],
            )

    def test_validate_splits_allows_small_rounding(self) -> None:
        """Should allow rounding differences up to 0.01."""
        tag_id1, tag_id2 = uuid4(), uuid4()
        # 33.33 + 33.33 + 33.33 = 99.99, which is 0.01 less than 100
        validate_splits(
            Decimal("-100.00"),
            [
                (tag_id1, Decimal("33.33")),
                (tag_id2, Decimal("66.67")),
            ],
        )
        # Should pass


class TestTransactionSplits:
    """Tests for transaction split CRUD operations."""

    def _create_transaction(
        self,
        db_session: Session,
        account: Account,
        amount: Decimal = Decimal("-100.00"),
    ) -> Transaction:
        """Create a test transaction."""
        txn = Transaction(
            account_id=account.id,
            provider_id=f"txn-{uuid4()}",
            booking_date=datetime.now(UTC),
            amount=amount,
            currency="GBP",
            synced_at=datetime.now(UTC),
        )
        db_session.add(txn)
        db_session.flush()
        return txn

    def test_set_transaction_splits(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should create splits for a transaction."""
        tag1 = create_tag(db_session, test_user.id, "Groceries")
        tag2 = create_tag(db_session, test_user.id, "Household")
        txn = self._create_transaction(db_session, test_account, Decimal("-100.00"))
        db_session.commit()

        splits = set_transaction_splits(
            db_session,
            txn,
            [(tag1.id, Decimal("60.00")), (tag2.id, Decimal("40.00"))],
        )
        db_session.commit()

        assert len(splits) == 2
        amounts = {float(s.amount) for s in splits}
        assert amounts == {60.00, 40.00}

    def test_set_transaction_splits_replaces_existing(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should replace existing splits when setting new ones."""
        tag1 = create_tag(db_session, test_user.id, "Groceries")
        tag2 = create_tag(db_session, test_user.id, "Household")
        tag3 = create_tag(db_session, test_user.id, "Other")
        txn = self._create_transaction(db_session, test_account, Decimal("-100.00"))
        db_session.commit()

        # Set initial splits
        set_transaction_splits(
            db_session,
            txn,
            [(tag1.id, Decimal("60.00")), (tag2.id, Decimal("40.00"))],
        )
        db_session.commit()

        # Replace with new splits
        new_splits = set_transaction_splits(
            db_session,
            txn,
            [(tag3.id, Decimal("100.00"))],
        )
        db_session.commit()

        assert len(new_splits) == 1
        assert new_splits[0].tag_id == tag3.id
        assert float(new_splits[0].amount) == 100.00

        # Verify old splits are gone
        all_splits = get_transaction_splits(db_session, txn.id)
        assert len(all_splits) == 1

    def test_get_transaction_splits(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should retrieve splits for a transaction."""
        tag1 = create_tag(db_session, test_user.id, "Groceries")
        tag2 = create_tag(db_session, test_user.id, "Household")
        txn = self._create_transaction(db_session, test_account, Decimal("-100.00"))
        db_session.commit()

        set_transaction_splits(
            db_session,
            txn,
            [(tag1.id, Decimal("60.00")), (tag2.id, Decimal("40.00"))],
        )
        db_session.commit()

        splits = get_transaction_splits(db_session, txn.id)
        assert len(splits) == 2

    def test_get_transaction_splits_empty(self, db_session: Session, test_account: Account) -> None:
        """Should return empty list for transaction with no splits."""
        txn = self._create_transaction(db_session, test_account)
        db_session.commit()

        splits = get_transaction_splits(db_session, txn.id)
        assert splits == []

    def test_clear_transaction_splits(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should remove all splits from a transaction."""
        tag1 = create_tag(db_session, test_user.id, "Groceries")
        tag2 = create_tag(db_session, test_user.id, "Household")
        txn = self._create_transaction(db_session, test_account, Decimal("-100.00"))
        db_session.commit()

        set_transaction_splits(
            db_session,
            txn,
            [(tag1.id, Decimal("60.00")), (tag2.id, Decimal("40.00"))],
        )
        db_session.commit()

        result = clear_transaction_splits(db_session, txn.id)
        db_session.commit()

        assert result is True
        splits = get_transaction_splits(db_session, txn.id)
        assert splits == []

    def test_clear_transaction_splits_returns_false_when_empty(
        self, db_session: Session, test_account: Account
    ) -> None:
        """Should return False when no splits to clear."""
        txn = self._create_transaction(db_session, test_account)
        db_session.commit()

        result = clear_transaction_splits(db_session, txn.id)
        assert result is False

    def test_get_splits_with_tags(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should return splits with their associated tag data."""
        tag1 = create_tag(db_session, test_user.id, "Groceries", colour="#22c55e")
        tag2 = create_tag(db_session, test_user.id, "Household", colour="#3b82f6")
        txn = self._create_transaction(db_session, test_account, Decimal("-100.00"))
        db_session.commit()

        set_transaction_splits(
            db_session,
            txn,
            [(tag1.id, Decimal("60.00")), (tag2.id, Decimal("40.00"))],
        )
        db_session.commit()

        splits_with_tags = get_splits_with_tags(db_session, txn.id)

        assert len(splits_with_tags) == 2
        for split, tag in splits_with_tags:
            assert isinstance(split, TransactionSplit)
            assert tag.name in ["Groceries", "Household"]

    def test_set_splits_validates_sum(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should raise error when splits don't sum to transaction amount."""
        tag1 = create_tag(db_session, test_user.id, "Groceries")
        txn = self._create_transaction(db_session, test_account, Decimal("-100.00"))
        db_session.commit()

        with pytest.raises(SplitValidationError, match="must equal transaction amount"):
            set_transaction_splits(
                db_session,
                txn,
                [(tag1.id, Decimal("50.00"))],  # Only 50 of 100
            )
