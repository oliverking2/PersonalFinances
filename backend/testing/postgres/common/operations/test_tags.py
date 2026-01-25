"""Tests for tag database operations."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.models import Account, Transaction
from src.postgres.common.operations.tags import (
    MAX_TAGS_PER_TRANSACTION,
    add_tags_to_transaction,
    bulk_tag_transactions,
    count_tags_by_user_id,
    create_tag,
    delete_tag,
    get_tag_by_id,
    get_tag_by_name,
    get_tag_usage_counts,
    get_tags_by_user_id,
    remove_tag_from_transaction,
    update_tag,
)


class TestTagCRUD:
    """Tests for tag CRUD operations."""

    def test_create_tag(self, db_session: Session, test_user: User) -> None:
        """Should create a tag with name and colour."""
        tag = create_tag(db_session, test_user.id, "Groceries", "#10B981")
        db_session.commit()

        assert tag.id is not None
        assert tag.user_id == test_user.id
        assert tag.name == "Groceries"
        assert tag.colour == "#10B981"

    def test_create_tag_strips_whitespace(self, db_session: Session, test_user: User) -> None:
        """Should strip whitespace from tag name."""
        tag = create_tag(db_session, test_user.id, "  Groceries  ")
        db_session.commit()

        assert tag.name == "Groceries"

    def test_create_tag_truncates_long_name(self, db_session: Session, test_user: User) -> None:
        """Should truncate tag name to 50 characters."""
        long_name = "x" * 100
        tag = create_tag(db_session, test_user.id, long_name)
        db_session.commit()

        assert len(tag.name) == 50

    def test_get_tag_by_id(self, db_session: Session, test_user: User) -> None:
        """Should retrieve tag by ID."""
        tag = create_tag(db_session, test_user.id, "Test")
        db_session.commit()

        result = get_tag_by_id(db_session, tag.id)
        assert result is not None
        assert result.id == tag.id

    def test_get_tag_by_id_not_found(self, db_session: Session) -> None:
        """Should return None for non-existent tag."""
        result = get_tag_by_id(db_session, uuid4())
        assert result is None

    def test_get_tags_by_user_id(self, db_session: Session, test_user: User) -> None:
        """Should retrieve all tags for a user ordered by name."""
        create_tag(db_session, test_user.id, "Zebra")
        create_tag(db_session, test_user.id, "Apple")
        create_tag(db_session, test_user.id, "Mango")
        db_session.commit()

        tags = get_tags_by_user_id(db_session, test_user.id)
        assert len(tags) == 3
        assert [t.name for t in tags] == ["Apple", "Mango", "Zebra"]

    def test_get_tag_by_name(self, db_session: Session, test_user: User) -> None:
        """Should find tag by user and name."""
        create_tag(db_session, test_user.id, "Test")
        db_session.commit()

        result = get_tag_by_name(db_session, test_user.id, "Test")
        assert result is not None
        assert result.name == "Test"

    def test_get_tag_by_name_not_found(self, db_session: Session, test_user: User) -> None:
        """Should return None if tag name not found."""
        result = get_tag_by_name(db_session, test_user.id, "NonExistent")
        assert result is None

    def test_count_tags_by_user_id(self, db_session: Session, test_user: User) -> None:
        """Should count tags for a user."""
        create_tag(db_session, test_user.id, "One")
        create_tag(db_session, test_user.id, "Two")
        db_session.commit()

        count = count_tags_by_user_id(db_session, test_user.id)
        assert count == 2

    def test_update_tag_name(self, db_session: Session, test_user: User) -> None:
        """Should update tag name."""
        tag = create_tag(db_session, test_user.id, "Old Name")
        db_session.commit()

        updated = update_tag(db_session, tag.id, name="New Name")
        db_session.commit()

        assert updated is not None
        assert updated.name == "New Name"

    def test_update_tag_colour(self, db_session: Session, test_user: User) -> None:
        """Should update tag colour."""
        tag = create_tag(db_session, test_user.id, "Test", "#000000")
        db_session.commit()

        updated = update_tag(db_session, tag.id, colour="#FFFFFF")
        db_session.commit()

        assert updated is not None
        assert updated.colour == "#FFFFFF"

    def test_update_tag_clear_colour(self, db_session: Session, test_user: User) -> None:
        """Should clear tag colour when set to None."""
        tag = create_tag(db_session, test_user.id, "Test", "#000000")
        db_session.commit()

        updated = update_tag(db_session, tag.id, colour=None)
        db_session.commit()

        assert updated is not None
        assert updated.colour is None

    def test_update_tag_not_found(self, db_session: Session) -> None:
        """Should return None when updating non-existent tag."""
        result = update_tag(db_session, uuid4(), name="Test")
        assert result is None

    def test_delete_tag(self, db_session: Session, test_user: User) -> None:
        """Should delete tag."""
        tag = create_tag(db_session, test_user.id, "Test")
        db_session.commit()

        result = delete_tag(db_session, tag.id)
        db_session.commit()

        assert result is True
        assert get_tag_by_id(db_session, tag.id) is None

    def test_delete_tag_not_found(self, db_session: Session) -> None:
        """Should return False when deleting non-existent tag."""
        result = delete_tag(db_session, uuid4())
        assert result is False


class TestTransactionTagging:
    """Tests for transaction tagging operations."""

    def test_add_tags_to_transaction(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should add tags to a transaction."""
        tag1 = create_tag(db_session, test_user.id, "Tag1")
        tag2 = create_tag(db_session, test_user.id, "Tag2")
        txn = Transaction(
            account_id=test_account.id,
            provider_id="txn-001",
            booking_date=datetime(2024, 1, 15, tzinfo=UTC),
            amount=Decimal("-50.00"),
            currency="GBP",
            synced_at=datetime.now(UTC),
        )
        db_session.add(txn)
        db_session.commit()

        tags = add_tags_to_transaction(db_session, txn.id, [tag1.id, tag2.id])
        db_session.commit()

        assert len(tags) == 2
        assert {t.name for t in tags} == {"Tag1", "Tag2"}

    def test_add_tags_ignores_duplicates(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should not duplicate tags when adding same tag twice."""
        tag = create_tag(db_session, test_user.id, "Tag1")
        txn = Transaction(
            account_id=test_account.id,
            provider_id="txn-001",
            amount=Decimal("-50.00"),
            currency="GBP",
            synced_at=datetime.now(UTC),
        )
        db_session.add(txn)
        db_session.commit()

        add_tags_to_transaction(db_session, txn.id, [tag.id])
        tags = add_tags_to_transaction(db_session, txn.id, [tag.id])
        db_session.commit()

        assert len(tags) == 1

    def test_add_tags_respects_limit(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should respect the maximum tags per transaction limit."""
        tags = [create_tag(db_session, test_user.id, f"Tag{i}") for i in range(15)]
        txn = Transaction(
            account_id=test_account.id,
            provider_id="txn-001",
            amount=Decimal("-50.00"),
            currency="GBP",
            synced_at=datetime.now(UTC),
        )
        db_session.add(txn)
        db_session.commit()

        result_tags = add_tags_to_transaction(db_session, txn.id, [t.id for t in tags])
        db_session.commit()

        assert len(result_tags) == MAX_TAGS_PER_TRANSACTION

    def test_remove_tag_from_transaction(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should remove a tag from a transaction."""
        tag1 = create_tag(db_session, test_user.id, "Tag1")
        tag2 = create_tag(db_session, test_user.id, "Tag2")
        txn = Transaction(
            account_id=test_account.id,
            provider_id="txn-001",
            amount=Decimal("-50.00"),
            currency="GBP",
            synced_at=datetime.now(UTC),
        )
        db_session.add(txn)
        db_session.commit()

        add_tags_to_transaction(db_session, txn.id, [tag1.id, tag2.id])
        tags = remove_tag_from_transaction(db_session, txn.id, tag1.id)
        db_session.commit()

        assert len(tags) == 1
        assert tags[0].name == "Tag2"

    def test_bulk_tag_transactions(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should bulk add tags to multiple transactions."""
        tag = create_tag(db_session, test_user.id, "Bulk")
        txns = [
            Transaction(
                account_id=test_account.id,
                provider_id=f"txn-{i}",
                amount=Decimal("-10.00"),
                currency="GBP",
                synced_at=datetime.now(UTC),
            )
            for i in range(3)
        ]
        db_session.add_all(txns)
        db_session.commit()

        count = bulk_tag_transactions(db_session, [t.id for t in txns], add_tag_ids=[tag.id])
        db_session.commit()

        assert count == 3
        for txn in txns:
            db_session.refresh(txn)
            assert len(txn.tags) == 1

    def test_bulk_tag_removes_tags(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should bulk remove tags from multiple transactions."""
        tag = create_tag(db_session, test_user.id, "ToRemove")
        txns = [
            Transaction(
                account_id=test_account.id,
                provider_id=f"txn-{i}",
                amount=Decimal("-10.00"),
                currency="GBP",
                synced_at=datetime.now(UTC),
            )
            for i in range(2)
        ]
        db_session.add_all(txns)
        db_session.commit()

        # Add tags first
        for txn in txns:
            add_tags_to_transaction(db_session, txn.id, [tag.id])
        db_session.commit()

        # Now bulk remove
        count = bulk_tag_transactions(db_session, [t.id for t in txns], remove_tag_ids=[tag.id])
        db_session.commit()

        assert count == 2
        for txn in txns:
            db_session.refresh(txn)
            assert len(txn.tags) == 0


class TestTagUsageCounts:
    """Tests for tag usage count operations."""

    def test_get_tag_usage_counts(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should return usage counts for tags."""
        tag1 = create_tag(db_session, test_user.id, "Used")
        tag2 = create_tag(db_session, test_user.id, "Unused")
        txn = Transaction(
            account_id=test_account.id,
            provider_id="txn-001",
            amount=Decimal("-50.00"),
            currency="GBP",
            synced_at=datetime.now(UTC),
        )
        db_session.add(txn)
        db_session.commit()

        add_tags_to_transaction(db_session, txn.id, [tag1.id])
        db_session.commit()

        counts = get_tag_usage_counts(db_session, test_user.id)

        assert counts[tag1.id] == 1
        assert counts[tag2.id] == 0
