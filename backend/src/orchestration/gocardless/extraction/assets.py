"""GoCardless Dagster Extraction Assets.

These assets extract data from the GoCardless API and write to Postgres.
dbt then reads from Postgres and transforms into DuckDB for analytics.
"""

from datetime import date

from dagster import (
    AssetExecutionContext,
    AssetKey,
    Definitions,
    asset,
)
from dateutil.relativedelta import relativedelta

from src.orchestration.resources import PostgresDatabase
from src.postgres.gocardless.operations.balances import upsert_balances
from src.postgres.gocardless.operations.bank_accounts import (
    get_active_accounts,
    get_transaction_watermark,
    update_transaction_watermark,
    upsert_bank_account_details,
)
from src.postgres.gocardless.operations.institutions import upsert_institutions
from src.postgres.gocardless.operations.requisitions import upsert_requisitions
from src.postgres.gocardless.operations.transactions import upsert_transactions
from src.providers.gocardless.api.account import (
    get_account_details_by_id,
    get_balance_data_by_id,
    get_transaction_data_by_id,
)
from src.providers.gocardless.api.core import GoCardlessCredentials, GoCardlessRateLimitError
from src.providers.gocardless.api.institutions import get_institutions
from src.providers.gocardless.api.requisition import get_all_requisition_data


@asset(
    key=AssetKey(["source", "gocardless", "extract", "transactions"]),
    group_name="gocardless",
    description="Extract transactions from GoCardless to Postgres.",
    required_resource_keys={"gocardless_api", "postgres_database"},
)
def gocardless_extract_transactions(context: AssetExecutionContext) -> None:
    """Extract bank account transactions from GoCardless to Postgres."""
    creds: GoCardlessCredentials = context.resources.gocardless_api
    postgres_database: PostgresDatabase = context.resources.postgres_database

    today = date.today()

    with postgres_database.get_session() as session:
        for account in get_active_accounts(session):
            watermark = get_transaction_watermark(session, account.id)

            context.log.info(f"Watermark for account {account.id}: {watermark}")
            date_start = today + relativedelta(days=-90) if watermark is None else watermark

            # Go a few days further back to add some overlap in case any data was missed
            date_start += relativedelta(days=-3)

            context.log.info(
                f"Extracting transactions for account {account.id} from {date_start} to {today}"
            )

            try:
                raw_transactions = get_transaction_data_by_id(
                    creds, account.id, date_start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
                )
            except GoCardlessRateLimitError:
                context.log.warning(f"Rate limit exceeded for account {account.id}")
                continue

            # Upsert to Postgres
            count = upsert_transactions(session, account.id, raw_transactions)
            context.log.info(f"Upserted {count} transactions for account {account.id}")

            update_transaction_watermark(session, account.id, today)
            context.log.info(f"Updated watermark for account {account.id}")


@asset(
    key=AssetKey(["source", "gocardless", "extract", "account_details"]),
    group_name="gocardless",
    description="Extract account details from GoCardless to Postgres.",
    required_resource_keys={"gocardless_api", "postgres_database"},
)
def gocardless_extract_account_details(context: AssetExecutionContext) -> None:
    """Extract bank account details from GoCardless to Postgres."""
    creds: GoCardlessCredentials = context.resources.gocardless_api
    postgres_database: PostgresDatabase = context.resources.postgres_database

    with postgres_database.get_session() as session:
        accounts = get_active_accounts(session)
        for account in accounts:
            context.log.info(f"Extracting account details for {account.id}")

            account_data = get_account_details_by_id(creds, account.id)

            upsert_bank_account_details(session, account.id, account_data)
            context.log.info(f"Updated account details for {account.id}")


@asset(
    key=AssetKey(["source", "gocardless", "extract", "account_balances"]),
    group_name="gocardless",
    description="Extract account balances from GoCardless to Postgres.",
    required_resource_keys={"gocardless_api", "postgres_database"},
)
def gocardless_extract_balances(context: AssetExecutionContext) -> None:
    """Extract bank account balances from GoCardless to Postgres."""
    creds: GoCardlessCredentials = context.resources.gocardless_api
    postgres_database: PostgresDatabase = context.resources.postgres_database

    with postgres_database.get_session() as session:
        accounts = get_active_accounts(session)
        for account in accounts:
            context.log.info(f"Extracting balance for account {account.id}")

            balance_data = get_balance_data_by_id(creds, account.id)

            count = upsert_balances(session, account.id, balance_data)
            context.log.info(f"Upserted {count} balances for account {account.id}")


@asset(
    key=AssetKey(["source", "gocardless", "extract", "institutions"]),
    group_name="gocardless",
    description="Extract institutions from GoCardless to Postgres.",
    required_resource_keys={"gocardless_api", "postgres_database"},
)
def gocardless_extract_institutions(context: AssetExecutionContext) -> None:
    """Extract institution metadata from GoCardless to Postgres."""
    creds: GoCardlessCredentials = context.resources.gocardless_api
    postgres_database: PostgresDatabase = context.resources.postgres_database

    context.log.info("Fetching institutions from GoCardless API")
    institutions = get_institutions(creds)
    context.log.info(f"Fetched {len(institutions)} institutions from GoCardless")

    with postgres_database.get_session() as session:
        count = upsert_institutions(session, institutions)
        context.log.info(f"Upserted {count} institutions into gc_institutions")


@asset(
    key=AssetKey(["source", "gocardless", "extract", "requisitions"]),
    group_name="gocardless",
    description="Extract requisition status from GoCardless to Postgres.",
    required_resource_keys={"gocardless_api", "postgres_database"},
)
def gocardless_extract_requisitions(context: AssetExecutionContext) -> None:
    """Extract requisition status from GoCardless to Postgres.

    Updates existing requisitions with latest status from GoCardless API.
    Does not create new requisitions (those are created via OAuth flow).
    """
    creds: GoCardlessCredentials = context.resources.gocardless_api
    postgres_database: PostgresDatabase = context.resources.postgres_database

    context.log.info("Fetching requisitions from GoCardless API")
    requisitions = get_all_requisition_data(creds)
    context.log.info(f"Fetched {len(requisitions)} requisitions from GoCardless")

    with postgres_database.get_session() as session:
        count = upsert_requisitions(session, requisitions)
        context.log.info(f"Updated {count} requisitions in gc_requisition_links")


extraction_asset_defs = Definitions(
    assets=[
        gocardless_extract_transactions,
        gocardless_extract_account_details,
        gocardless_extract_balances,
        gocardless_extract_institutions,
        gocardless_extract_requisitions,
    ]
)
