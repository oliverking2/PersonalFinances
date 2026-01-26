"""Tests for tag rule database operations."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.models import Account, Transaction
from src.postgres.common.operations.tag_rules import (
    apply_rule_to_transaction,
    bulk_apply_rules,
    create_tag_rule,
    delete_tag_rule,
    get_tag_rule_by_id,
    get_tag_rules_by_user_id,
    reorder_tag_rules,
    transaction_matches_rule,
    update_tag_rule,
)
from src.postgres.common.operations.tags import create_tag


class TestTagRuleCRUD:
    """Tests for tag rule CRUD operations."""

    def test_create_tag_rule(self, db_session: Session, test_user: User) -> None:
        """Should create a tag rule with conditions."""
        tag = create_tag(db_session, test_user.id, "Groceries")
        db_session.flush()

        rule = create_tag_rule(
            db_session,
            user_id=test_user.id,
            name="Tesco Rule",
            tag_id=tag.id,
            conditions={"merchant_contains": "tesco"},
        )
        db_session.commit()

        assert rule.id is not None
        assert rule.user_id == test_user.id
        assert rule.name == "Tesco Rule"
        assert rule.tag_id == tag.id
        assert rule.conditions.get("merchant_contains") == "tesco"
        assert rule.enabled is True
        assert rule.priority == 1

    def test_create_multiple_rules_sets_priority(
        self, db_session: Session, test_user: User
    ) -> None:
        """Should set incremental priority for new rules."""
        tag = create_tag(db_session, test_user.id, "Test")
        db_session.flush()

        rule1 = create_tag_rule(db_session, test_user.id, "Rule 1", tag.id)
        rule2 = create_tag_rule(db_session, test_user.id, "Rule 2", tag.id)
        rule3 = create_tag_rule(db_session, test_user.id, "Rule 3", tag.id)
        db_session.commit()

        assert rule1.priority == 1
        assert rule2.priority == 2
        assert rule3.priority == 3

    def test_get_tag_rule_by_id(self, db_session: Session, test_user: User) -> None:
        """Should retrieve rule by ID."""
        tag = create_tag(db_session, test_user.id, "Test")
        db_session.flush()
        rule = create_tag_rule(db_session, test_user.id, "Test Rule", tag.id)
        db_session.commit()

        result = get_tag_rule_by_id(db_session, rule.id)
        assert result is not None
        assert result.id == rule.id

    def test_get_tag_rule_by_id_not_found(self, db_session: Session) -> None:
        """Should return None for non-existent rule."""
        result = get_tag_rule_by_id(db_session, uuid4())
        assert result is None

    def test_get_tag_rules_by_user_id(self, db_session: Session, test_user: User) -> None:
        """Should retrieve all rules for a user ordered by priority."""
        tag = create_tag(db_session, test_user.id, "Test")
        db_session.flush()
        create_tag_rule(db_session, test_user.id, "Rule A", tag.id)
        create_tag_rule(db_session, test_user.id, "Rule B", tag.id)
        db_session.commit()

        rules = get_tag_rules_by_user_id(db_session, test_user.id)
        assert len(rules) == 2
        assert rules[0].name == "Rule A"
        assert rules[1].name == "Rule B"

    def test_get_tag_rules_by_user_id_filter_by_tag(
        self, db_session: Session, test_user: User
    ) -> None:
        """Should filter rules by target tag."""
        tag1 = create_tag(db_session, test_user.id, "Tag1")
        tag2 = create_tag(db_session, test_user.id, "Tag2")
        db_session.flush()
        create_tag_rule(db_session, test_user.id, "Rule 1", tag1.id)
        create_tag_rule(db_session, test_user.id, "Rule 2", tag2.id)
        db_session.commit()

        rules = get_tag_rules_by_user_id(db_session, test_user.id, tag_id=tag1.id)
        assert len(rules) == 1
        assert rules[0].name == "Rule 1"

    def test_update_tag_rule(self, db_session: Session, test_user: User) -> None:
        """Should update rule properties."""
        tag = create_tag(db_session, test_user.id, "Test")
        db_session.flush()
        rule = create_tag_rule(db_session, test_user.id, "Old Name", tag.id)
        db_session.commit()

        updated = update_tag_rule(
            db_session,
            rule.id,
            name="New Name",
            enabled=False,
            conditions={"merchant_contains": "walmart"},
        )
        db_session.commit()

        assert updated is not None
        assert updated.name == "New Name"
        assert updated.enabled is False
        assert updated.conditions.get("merchant_contains") == "walmart"

    def test_delete_tag_rule(self, db_session: Session, test_user: User) -> None:
        """Should delete a tag rule."""
        tag = create_tag(db_session, test_user.id, "Test")
        db_session.flush()
        rule = create_tag_rule(db_session, test_user.id, "Test Rule", tag.id)
        db_session.commit()

        result = delete_tag_rule(db_session, rule.id)
        db_session.commit()

        assert result is True
        assert get_tag_rule_by_id(db_session, rule.id) is None

    def test_reorder_tag_rules(self, db_session: Session, test_user: User) -> None:
        """Should update priorities based on given order."""
        tag = create_tag(db_session, test_user.id, "Test")
        db_session.flush()
        rule1 = create_tag_rule(db_session, test_user.id, "Rule 1", tag.id)
        rule2 = create_tag_rule(db_session, test_user.id, "Rule 2", tag.id)
        rule3 = create_tag_rule(db_session, test_user.id, "Rule 3", tag.id)
        db_session.commit()

        # Reorder: Rule 3 first, then Rule 1, then Rule 2
        reorder_tag_rules(db_session, test_user.id, [rule3.id, rule1.id, rule2.id])
        db_session.commit()

        rules = get_tag_rules_by_user_id(db_session, test_user.id)
        assert [r.name for r in rules] == ["Rule 3", "Rule 1", "Rule 2"]


class TestRuleMatching:
    """Tests for rule matching logic."""

    def _create_transaction(
        self,
        db_session: Session,
        account: Account,
        counterparty_name: str | None = None,
        description: str | None = None,
        amount: Decimal = Decimal("-10.00"),
    ) -> Transaction:
        """Create a test transaction."""
        txn = Transaction(
            account_id=account.id,
            provider_id=f"txn-{uuid4()}",
            booking_date=datetime.now(UTC),
            amount=amount,
            currency="GBP",
            counterparty_name=counterparty_name,
            description=description,
            synced_at=datetime.now(UTC),
        )
        db_session.add(txn)
        db_session.flush()
        return txn

    def test_matches_merchant_contains(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should match when merchant name contains the pattern."""
        tag = create_tag(db_session, test_user.id, "Test")
        db_session.flush()
        rule = create_tag_rule(
            db_session, test_user.id, "Test", tag.id, conditions={"merchant_contains": "tesco"}
        )
        db_session.commit()

        txn_match = self._create_transaction(
            db_session, test_account, counterparty_name="TESCO STORES LTD"
        )
        txn_no_match = self._create_transaction(
            db_session, test_account, counterparty_name="SAINSBURYS"
        )

        assert transaction_matches_rule(txn_match, rule) is True
        assert transaction_matches_rule(txn_no_match, rule) is False

    def test_matches_merchant_exact(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should match when merchant name matches exactly."""
        tag = create_tag(db_session, test_user.id, "Test")
        db_session.flush()
        rule = create_tag_rule(
            db_session, test_user.id, "Test", tag.id, conditions={"merchant_exact": "TESCO"}
        )
        db_session.commit()

        txn_match = self._create_transaction(db_session, test_account, counterparty_name="TESCO")
        txn_no_match = self._create_transaction(
            db_session, test_account, counterparty_name="TESCO STORES"
        )

        assert transaction_matches_rule(txn_match, rule) is True
        assert transaction_matches_rule(txn_no_match, rule) is False

    def test_matches_description_contains(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should match when description contains the pattern."""
        tag = create_tag(db_session, test_user.id, "Test")
        db_session.flush()
        rule = create_tag_rule(
            db_session,
            test_user.id,
            "Test",
            tag.id,
            conditions={"description_contains": "subscription"},
        )
        db_session.commit()

        txn_match = self._create_transaction(
            db_session, test_account, description="Monthly subscription payment"
        )
        txn_no_match = self._create_transaction(
            db_session, test_account, description="One-time payment"
        )

        assert transaction_matches_rule(txn_match, rule) is True
        assert transaction_matches_rule(txn_no_match, rule) is False

    def test_matches_amount_range(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should match when amount is within range."""
        tag = create_tag(db_session, test_user.id, "Test")
        db_session.flush()
        rule = create_tag_rule(
            db_session,
            test_user.id,
            "Test",
            tag.id,
            conditions={"min_amount": 10.00, "max_amount": 50.00},
        )
        db_session.commit()

        txn_match = self._create_transaction(db_session, test_account, amount=Decimal("-25.00"))
        txn_too_small = self._create_transaction(db_session, test_account, amount=Decimal("-5.00"))
        txn_too_large = self._create_transaction(
            db_session, test_account, amount=Decimal("-100.00")
        )

        assert transaction_matches_rule(txn_match, rule) is True
        assert transaction_matches_rule(txn_too_small, rule) is False
        assert transaction_matches_rule(txn_too_large, rule) is False

    def test_excludes_merchant_not_contains(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should exclude when merchant contains exclusion pattern."""
        tag = create_tag(db_session, test_user.id, "Test")
        db_session.flush()
        rule = create_tag_rule(
            db_session,
            test_user.id,
            "Test",
            tag.id,
            conditions={"merchant_contains": "supermarket", "merchant_not_contains": "online"},
        )
        db_session.commit()

        txn_match = self._create_transaction(
            db_session, test_account, counterparty_name="TESCO SUPERMARKET"
        )
        txn_excluded = self._create_transaction(
            db_session, test_account, counterparty_name="TESCO SUPERMARKET ONLINE"
        )

        assert transaction_matches_rule(txn_match, rule) is True
        assert transaction_matches_rule(txn_excluded, rule) is False


class TestApplyRules:
    """Tests for applying rules to transactions."""

    def _create_transaction(
        self,
        db_session: Session,
        account: Account,
        counterparty_name: str | None = None,
    ) -> Transaction:
        """Create a test transaction."""
        txn = Transaction(
            account_id=account.id,
            provider_id=f"txn-{uuid4()}",
            booking_date=datetime.now(UTC),
            amount=Decimal("-10.00"),
            currency="GBP",
            counterparty_name=counterparty_name,
            synced_at=datetime.now(UTC),
        )
        db_session.add(txn)
        db_session.flush()
        return txn

    def test_apply_rule_to_transaction(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should apply rule's tag to matching transaction."""
        tag = create_tag(db_session, test_user.id, "Groceries")
        db_session.flush()
        rule = create_tag_rule(
            db_session,
            test_user.id,
            "Grocery Rule",
            tag.id,
            conditions={"merchant_contains": "tesco"},
        )
        txn = self._create_transaction(db_session, test_account, counterparty_name="TESCO")
        db_session.commit()

        result = apply_rule_to_transaction(db_session, txn, rule)
        db_session.commit()

        assert result is True
        db_session.refresh(txn)
        assert len(txn.splits) == 1
        assert txn.splits[0].tag_id == tag.id
        assert txn.splits[0].is_auto is True

    def test_apply_rule_does_not_duplicate(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should not apply tag if already present."""
        tag = create_tag(db_session, test_user.id, "Groceries")
        db_session.flush()
        rule = create_tag_rule(db_session, test_user.id, "Grocery Rule", tag.id)
        txn = self._create_transaction(db_session, test_account)
        db_session.commit()

        # Apply twice
        apply_rule_to_transaction(db_session, txn, rule)
        result = apply_rule_to_transaction(db_session, txn, rule)
        db_session.commit()

        assert result is False  # Second application returns False (already tagged)
        db_session.refresh(txn)
        assert len(txn.splits) == 1  # Only one split

    def test_bulk_apply_rules(
        self, db_session: Session, test_user: User, test_account: Account
    ) -> None:
        """Should apply rules to multiple untagged transactions."""
        tag = create_tag(db_session, test_user.id, "Groceries")
        db_session.flush()
        create_tag_rule(
            db_session,
            test_user.id,
            "Grocery Rule",
            tag.id,
            conditions={"merchant_contains": "tesco"},
        )

        # Create matching transactions
        for i in range(3):
            self._create_transaction(db_session, test_account, counterparty_name=f"TESCO STORE {i}")
        # Create non-matching transaction
        self._create_transaction(db_session, test_account, counterparty_name="SAINSBURYS")
        db_session.commit()

        count = bulk_apply_rules(db_session, test_user.id)
        db_session.commit()

        assert count == 3  # Only matching transactions tagged
