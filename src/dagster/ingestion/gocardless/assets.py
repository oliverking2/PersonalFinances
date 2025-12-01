"""GoCardless Dagster Assets."""

from dagster import asset


@asset(name="extract_transactions_account_1")
def extract_transactions_account_1() -> int:
    """Extract transactions from account 1."""
    return 1
