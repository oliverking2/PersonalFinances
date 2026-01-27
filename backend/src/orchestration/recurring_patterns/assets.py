"""Recurring patterns sync assets.

Syncs detected recurring patterns from the dbt mart (DuckDB) to PostgreSQL.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from dagster import AssetExecutionContext, AssetKey, AutomationCondition, asset
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.duckdb.client import execute_query
from src.orchestration.resources import PostgresDatabase
from src.postgres.common.enums import RecurringFrequency
from src.postgres.common.models import (
    RecurringPattern,
    RecurringPatternTransaction,
    Transaction,
)
from src.postgres.common.operations.recurring_patterns import sync_detected_pattern


def _extract_merchant_name(merchant_pattern: str) -> str:
    """Extract the clean merchant name from a pattern key.

    The dbt model stores patterns as 'merchant_name_£XX' where XX is the amount bucket.
    This extracts just the merchant name for transaction matching.

    :param merchant_pattern: Pattern key (e.g., 'netflix_£15').
    :return: Clean merchant name (e.g., 'netflix').
    """
    # Pattern format: merchant_name_£XX (amount bucket suffix)
    # Find the last occurrence of '_£' and strip everything after
    suffix_idx = merchant_pattern.rfind("_£")
    if suffix_idx > 0:
        return merchant_pattern[:suffix_idx]
    return merchant_pattern


def _link_transactions_to_pattern(
    session: Session,
    pattern: RecurringPattern,
) -> int:
    """Link matching transactions to a recurring pattern.

    Finds transactions with matching account_id and normalised merchant name,
    then creates RecurringPatternTransaction links for any that aren't already linked.

    :param session: SQLAlchemy session.
    :param pattern: The recurring pattern to link transactions to.
    :return: Number of newly linked transactions.
    """
    # Extract clean merchant name (without _£XX suffix from dbt pattern key)
    merchant_name = _extract_merchant_name(pattern.merchant_pattern)

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

    # Get already linked transaction IDs
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
            link = RecurringPatternTransaction(
                pattern_id=pattern.id,
                transaction_id=txn.id,
                amount_match=True,  # Could compute actual match
                date_match=True,
            )
            session.add(link)
            linked_count += 1

    if linked_count > 0:
        session.flush()

    return linked_count


@asset(
    key=AssetKey(["sync", "recurring", "patterns"]),
    deps=[AssetKey(["mart", "fct_recurring_patterns"])],
    group_name="recurring_patterns",
    description="Sync detected recurring patterns from dbt mart to PostgreSQL.",
    required_resource_keys={"postgres_database"},
    automation_condition=AutomationCondition.any_deps_updated(),
)
def sync_recurring_patterns(context: AssetExecutionContext) -> None:
    """Sync recurring patterns from dbt fct_recurring_patterns to PostgreSQL.

    This asset:
    1. Queries the dbt mart for detected patterns
    2. For each pattern, checks if it exists in PostgreSQL
    3. Creates new patterns or updates existing 'detected' ones
    4. Preserves user decisions (confirmed/dismissed/paused/manual not touched)
    """
    postgres_database: PostgresDatabase = context.resources.postgres_database

    # Query detected patterns from dbt mart
    query = """
        SELECT
            user_id,
            account_id,
            merchant_pattern,
            display_name,
            expected_amount,
            amount_variance,
            currency,
            frequency,
            confidence_score,
            occurrence_count,
            last_occurrence_date,
            next_expected_date,
            status
        FROM main_mart.fct_recurring_patterns
        WHERE status = 'detected'
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
                # Parse frequency enum (DuckDB returns uppercase column names)
                frequency_str = row["FREQUENCY"]
                try:
                    frequency = RecurringFrequency(frequency_str)
                except ValueError:
                    context.log.warning(
                        f"Unknown frequency '{frequency_str}' for {row['MERCHANT_PATTERN']}"
                    )
                    skipped_count += 1
                    continue

                # Parse dates - DuckDB returns datetime objects with timezone
                last_occurrence = row["LAST_OCCURRENCE_DATE"]
                if isinstance(last_occurrence, str):
                    last_occurrence = datetime.fromisoformat(last_occurrence)
                elif not isinstance(last_occurrence, datetime):
                    # It's a date, convert to datetime
                    last_occurrence = datetime.combine(last_occurrence, datetime.min.time())

                next_expected = row["NEXT_EXPECTED_DATE"]
                if next_expected:
                    if isinstance(next_expected, str):
                        next_expected = datetime.fromisoformat(next_expected)
                    elif not isinstance(next_expected, datetime):
                        next_expected = datetime.combine(next_expected, datetime.min.time())

                # Sync the pattern
                pattern, created = sync_detected_pattern(
                    session=session,
                    user_id=UUID(str(row["USER_ID"])),
                    account_id=UUID(str(row["ACCOUNT_ID"])),
                    merchant_pattern=str(row["MERCHANT_PATTERN"]),
                    expected_amount=Decimal(str(row["EXPECTED_AMOUNT"])),
                    frequency=frequency,
                    confidence_score=Decimal(str(row["CONFIDENCE_SCORE"])),
                    occurrence_count=int(row["OCCURRENCE_COUNT"]),
                    last_occurrence_date=last_occurrence,
                    next_expected_date=next_expected,
                    display_name=row.get("DISPLAY_NAME"),
                    currency=str(row.get("CURRENCY", "GBP")),
                    amount_variance=Decimal(str(row.get("AMOUNT_VARIANCE", 0))),
                )

                # Link matching transactions to this pattern
                _link_transactions_to_pattern(session, pattern)

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            except Exception as e:
                context.log.warning(
                    f"Failed to sync pattern for {row.get('MERCHANT_PATTERN')}: {e}"
                )
                skipped_count += 1

    context.log.info(
        f"Sync complete: created={created_count}, updated={updated_count}, skipped={skipped_count}"
    )
