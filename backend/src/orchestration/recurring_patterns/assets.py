"""Recurring patterns sync assets.

Syncs detected recurring patterns from the dbt mart (DuckDB) to PostgreSQL.
Uses opt-in model: patterns are created as PENDING for user review.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from dagster import AssetExecutionContext, AssetKey, AutomationCondition, asset
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.duckdb.client import execute_query
from src.orchestration.resources import PostgresDatabase
from src.postgres.common.enums import RecurringDirection, RecurringFrequency
from src.postgres.common.models import (
    RecurringPattern,
    RecurringPatternTransaction,
    Transaction,
)
from src.postgres.common.operations.recurring_patterns import (
    link_transaction_to_pattern,
    sync_detected_pattern,
)


def _extract_merchant_name(merchant_key: str) -> str:
    """Extract the clean merchant name from a dbt pattern key.

    The dbt model stores patterns as 'merchant_name_exp_£XX' or 'merchant_name_inc_£XX'.
    This extracts just the merchant name for matching.

    :param merchant_key: Pattern key (e.g., 'netflix_exp_£15').
    :returns: Clean merchant name (e.g., 'netflix').
    """
    # First strip the amount bucket suffix (e.g., '_£15' or '_£15.0')
    suffix_idx = merchant_key.rfind("_£")
    name = merchant_key[:suffix_idx] if suffix_idx > 0 else merchant_key

    # Then strip the direction suffix if present (e.g., '_exp' or '_inc')
    if name.endswith("_exp") or name.endswith("_inc"):
        name = name[:-4]

    return name


def _titlecase_merchant(merchant_name: str) -> str:
    """Convert merchant name to title case for display.

    :param merchant_name: Lowercase merchant name.
    :returns: Title-cased name.
    """
    # Handle common patterns
    return merchant_name.replace("_", " ").title()


def _link_transactions_to_pattern(
    session: Session,
    pattern: RecurringPattern,
    merchant_name: str,
) -> int:
    """Link matching transactions to a recurring pattern.

    Finds transactions with matching account_id and normalised merchant name,
    then creates links for any that aren't already linked.

    :param session: SQLAlchemy session.
    :param pattern: The recurring pattern to link transactions to.
    :param merchant_name: Clean merchant name for matching.
    :returns: Number of newly linked transactions.
    """
    # Find transactions that match this pattern
    # Normalise: lowercase, trimmed counterparty_name
    matching_txns = (
        session.query(Transaction)
        .filter(
            Transaction.account_id == pattern.account_id,
            func.lower(func.trim(Transaction.counterparty_name)) == merchant_name.lower(),
        )
        .all()
    )

    # Get already linked transaction IDs (check by transaction_id which is unique)
    existing_links = (
        session.query(RecurringPatternTransaction.transaction_id)
        .filter(RecurringPatternTransaction.pattern_id == pattern.id)
        .all()
    )
    existing_txn_ids = {link[0] for link in existing_links}

    # Link new transactions
    linked_count = 0
    for txn in matching_txns:
        if txn.id not in existing_txn_ids:
            link = link_transaction_to_pattern(session, pattern.id, txn.id, is_manual=False)
            if link:
                linked_count += 1

    return linked_count


@asset(
    key=AssetKey(["sync", "recurring", "patterns"]),
    deps=[AssetKey(["mart", "int_recurring_candidates"])],
    group_name="recurring_patterns",
    description="Sync detected recurring patterns from dbt to PostgreSQL as pending.",
    required_resource_keys={"postgres_database"},
    automation_condition=AutomationCondition.any_deps_updated(),
)
def sync_recurring_patterns(  # noqa: PLR0912, PLR0915
    context: AssetExecutionContext,
) -> None:
    """Sync recurring patterns from int_recurring_candidates to PostgreSQL.

    This asset:
    1. Queries the dbt model for detected pattern candidates
    2. Creates new patterns as PENDING status (opt-in model)
    3. Updates existing pending patterns with latest data
    4. Preserves user decisions (active/paused/cancelled not touched)
    5. Links matching transactions to each pattern
    """
    postgres_database: PostgresDatabase = context.resources.postgres_database

    # Query detected patterns from int_recurring_candidates
    query = """
        SELECT
            user_id,
            account_id,
            merchant_key,
            merchant_name,
            latest_amount AS expected_amount,
            currency,
            detected_frequency AS frequency,
            confidence_score,
            occurrence_count,
            last_occurrence AS last_occurrence_date,
            -- Calculate next expected date based on frequency
            CASE detected_frequency
                WHEN 'weekly' THEN last_occurrence + INTERVAL '7 days'
                WHEN 'fortnightly' THEN last_occurrence + INTERVAL '14 days'
                WHEN 'monthly' THEN last_occurrence + INTERVAL '1 month'
                WHEN 'quarterly' THEN last_occurrence + INTERVAL '3 months'
                WHEN 'annual' THEN last_occurrence + INTERVAL '1 year'
            END AS next_expected_date,
            direction
        FROM main_mart.int_recurring_candidates
        WHERE
            confidence_score >= 0.2
            AND detected_frequency != 'irregular'
    """

    try:
        patterns = execute_query(query)
    except FileNotFoundError:
        context.log.warning("DuckDB database not found - skipping recurring patterns sync")
        return
    except Exception as e:
        context.log.error(f"Failed to query dbt mart: {e}")
        raise

    context.log.info(f"Found {len(patterns)} detected patterns in dbt mart")

    created_count = 0
    updated_count = 0
    skipped_count = 0

    with postgres_database.get_session() as session:
        for row in patterns:
            try:
                # Parse frequency enum
                frequency_str = row["frequency"]
                try:
                    frequency = RecurringFrequency(frequency_str)
                except ValueError:
                    context.log.warning(
                        f"Unknown frequency '{frequency_str}' for {row['merchant_key']}"
                    )
                    skipped_count += 1
                    continue

                # Parse dates - DuckDB returns datetime objects
                last_occurrence = row["last_occurrence_date"]
                if isinstance(last_occurrence, str):
                    last_occurrence = datetime.fromisoformat(last_occurrence)
                elif not isinstance(last_occurrence, datetime):
                    last_occurrence = datetime.combine(
                        last_occurrence, datetime.min.time(), tzinfo=UTC
                    )
                elif last_occurrence.tzinfo is None:
                    last_occurrence = last_occurrence.replace(tzinfo=UTC)

                next_expected = row["next_expected_date"]
                if next_expected:
                    if isinstance(next_expected, str):
                        next_expected = datetime.fromisoformat(next_expected)
                    elif not isinstance(next_expected, datetime):
                        next_expected = datetime.combine(
                            next_expected, datetime.min.time(), tzinfo=UTC
                        )
                    elif next_expected.tzinfo is None:
                        next_expected = next_expected.replace(tzinfo=UTC)

                # Parse direction
                direction_str = row.get("direction", "expense")
                direction = (
                    RecurringDirection.INCOME
                    if direction_str == "income"
                    else RecurringDirection.EXPENSE
                )

                # Extract merchant name for matching
                merchant_key = str(row["merchant_key"])
                merchant_name = _extract_merchant_name(merchant_key)
                display_name = _titlecase_merchant(row.get("merchant_name") or merchant_name)

                # Build detection reason
                detection_reason = (
                    f"Detected {row['occurrence_count']} transactions "
                    f"with {frequency_str} frequency"
                )

                # Sync the pattern (creates as PENDING or updates existing pending)
                pattern, created = sync_detected_pattern(
                    session=session,
                    user_id=UUID(str(row["user_id"])),
                    account_id=UUID(str(row["account_id"])),
                    name=display_name,
                    expected_amount=Decimal(str(row["expected_amount"])),
                    frequency=frequency,
                    direction=direction,
                    confidence_score=Decimal(str(row["confidence_score"])),
                    occurrence_count=int(row["occurrence_count"]),
                    last_occurrence_date=last_occurrence,
                    next_expected_date=next_expected,
                    merchant_contains=merchant_name,
                    currency=str(row.get("currency", "GBP")),
                    detection_reason=detection_reason,
                )

                # Link matching transactions to this pattern
                _link_transactions_to_pattern(session, pattern, merchant_name)

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            except Exception as e:
                context.log.warning(f"Failed to sync pattern for {row.get('merchant_key')}: {e}")
                skipped_count += 1

    context.log.info(
        f"Sync complete: created={created_count}, updated={updated_count}, skipped={skipped_count}"
    )
