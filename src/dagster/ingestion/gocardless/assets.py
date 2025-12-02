"""GoCardless Dagster Assets."""

from datetime import date

from dagster import asset, AutomationCondition, AssetExecutionContext
from dateutil.relativedelta import relativedelta

from src.gocardless.api.transactions import get_transaction_data_for_account
from src.postgres.gocardless.operations.bank_accounts import get_transaction_watermark


@asset(
    name="extract_transactions_account_1",
    required_resource_keys={"s3", "gocardless_api", "postgres_database"},
    automation_condition=AutomationCondition.on_cron("0 4 * * *"),
)
def extract_transactions_account_1(context: AssetExecutionContext) -> None:
    """Extract transactions from account 1."""
    account_id = "73ed675f-12fe-4d85-88d3-d439976ec662"

    creds = context.resources.gocardless_api
    # s3 = context.resources.s3
    postgres_database = context.resources.postgres_database

    watermark = get_transaction_watermark(postgres_database, account_id)
    date_start = date.today() + relativedelta(days=-90) if watermark is None else watermark

    # go a few days further back to add some overlap incase any data was missed
    date_start += relativedelta(days=-3)

    # get data from watermark till today
    raw_transactions = get_transaction_data_for_account(
        creds, account_id, date_start.strftime("%Y-%m-%d"), date.today().strftime("%Y-%m-%d")
    )

    print(raw_transactions)
