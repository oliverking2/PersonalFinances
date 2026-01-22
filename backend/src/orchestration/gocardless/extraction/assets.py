"""GoCardless Dagster Assets."""

import json
import os
import uuid
from datetime import date, datetime
from io import BytesIO

from dagster import (
    AssetExecutionContext,
    AssetKey,
    AutomationCondition,
    Definitions,
    asset,
)
from dateutil.relativedelta import relativedelta
from mypy_boto3_s3 import S3Client

from src.aws.s3 import upload_bytes_to_s3
from src.orchestration.resources import PostgresDatabase
from src.postgres.gocardless.operations.bank_accounts import (
    get_active_accounts,
    get_transaction_watermark,
    update_transaction_watermark,
)
from src.providers.gocardless.api.account import (
    get_account_details_by_id,
    get_balance_data_by_id,
    get_transaction_data_by_id,
)
from src.providers.gocardless.api.core import GoCardlessCredentials, GoCardlessRateLimitError


def _get_s3_bucket_name() -> str:
    """Get S3 bucket name from environment variable.

    :returns: The S3 bucket name.
    :raises ValueError: If S3_BUCKET_NAME environment variable is not set.
    """
    bucket_name = os.getenv("S3_BUCKET_NAME")
    if not bucket_name:
        raise ValueError("S3_BUCKET_NAME environment variable is not set")
    return bucket_name


@asset(
    key=AssetKey(["source", "gocardless", "extract", "transactions"]),
    group_name="gocardless",
    description="Extract transactions from GoCardless.",
    required_resource_keys={"s3", "gocardless_api", "postgres_database"},
    automation_condition=AutomationCondition.on_cron("0 4 * * *"),
)
def gocardless_extract_transactions(context: AssetExecutionContext) -> None:
    """Extract bank account transactions from GoCardless."""
    creds: GoCardlessCredentials = context.resources.gocardless_api
    s3: S3Client = context.resources.s3
    postgres_database: PostgresDatabase = context.resources.postgres_database

    today = date.today()

    with postgres_database.get_session() as session:
        for account in get_active_accounts(session):
            watermark = get_transaction_watermark(session, account.id)

            context.log.info(f"Watermark for account {account.id}: {watermark}")
            date_start = today + relativedelta(days=-90) if watermark is None else watermark

            # go a few days further back to add some overlap incase any data was missed
            date_start += relativedelta(days=-3)

            context.log.info(
                f"Extracting transactions for account {account.id} from {date_start} to {today}"
            )

            # get data from watermark till today
            try:
                raw_transactions = get_transaction_data_by_id(
                    creds, account.id, date_start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
                )
            except GoCardlessRateLimitError:
                context.log.warning(f"Rate limit exceeded for account {account.id}")
                continue

            # add the account ID to the data
            raw_transactions["account_id"] = account.id
            raw_transactions["_extract_dt"] = datetime.now().isoformat()

            raw_data = json.dumps(raw_transactions).encode("utf-8")

            # Upload to S3
            upload_bytes_to_s3(
                s3_client=s3,
                bucket_name=_get_s3_bucket_name(),
                prefix=f"extracts/gocardless/{account.id}/transactions/{today.year}/{today.month:02d}/{today.day:02d}",
                file_name=f"transactions_{uuid.uuid4()}.json",
                file_obj=BytesIO(raw_data),
            )
            context.log.info(f"Successfully uploaded transactions for account {account.id}")

            update_transaction_watermark(session, account.id, today)

            context.log.info(
                f"Successfully updated watermark for account {account.id} with date {today}"
            )


@asset(
    key=AssetKey(["source", "gocardless", "extract", "account_details"]),
    group_name="gocardless",
    description="Extract account details from GoCardless.",
    required_resource_keys={"s3", "gocardless_api", "postgres_database"},
    automation_condition=AutomationCondition.on_cron("0 4 * * *"),
)
def gocardless_extract_account_details(context: AssetExecutionContext) -> None:
    """Extract bank account details from GoCardless."""
    creds: GoCardlessCredentials = context.resources.gocardless_api
    postgres_database: PostgresDatabase = context.resources.postgres_database
    s3: S3Client = context.resources.s3

    today = date.today()

    with postgres_database.get_session() as session:
        accounts = get_active_accounts(session)
        for account in accounts:
            context.log.info(f"Extracting bank account details for account {account.id}")
            account_data = get_account_details_by_id(creds, account.id)

            # add the account ID to the data
            account_data["account_id"] = account.id
            account_data["_extract_dt"] = datetime.now().isoformat()

            raw_data = json.dumps(account_data).encode("utf-8")

            # Upload to S3
            upload_bytes_to_s3(
                s3_client=s3,
                bucket_name=_get_s3_bucket_name(),
                prefix=f"extracts/gocardless/{account.id}/details/{today.year}/{today.month:02d}/{today.day:02d}",
                file_name=f"details_{uuid.uuid4()}.json",
                file_obj=BytesIO(raw_data),
            )
            context.log.info(f"Successfully uploaded transactions for account {account.id}")


@asset(
    key=AssetKey(["source", "gocardless", "extract", "account_balances"]),
    group_name="gocardless",
    description="Extract account balances from GoCardless.",
    required_resource_keys={"s3", "gocardless_api", "postgres_database"},
    automation_condition=AutomationCondition.on_cron("0 4 * * *"),
)
def gocardless_extract_balances(context: AssetExecutionContext) -> None:
    """Extract bank account balances from GoCardless."""
    creds: GoCardlessCredentials = context.resources.gocardless_api
    postgres_database: PostgresDatabase = context.resources.postgres_database
    s3: S3Client = context.resources.s3

    today = date.today()

    with postgres_database.get_session() as session:
        accounts = get_active_accounts(session)
        for account in accounts:
            context.log.info(f"Extracting bank account balance for account {account.id}")
            balance_data = get_balance_data_by_id(creds, account.id)

            # add the account ID to the data
            balance_data["account_id"] = account.id
            balance_data["_extract_dt"] = datetime.now().isoformat()

            raw_data = json.dumps(balance_data).encode("utf-8")

            # Upload to S3
            upload_bytes_to_s3(
                s3_client=s3,
                bucket_name=_get_s3_bucket_name(),
                prefix=f"extracts/gocardless/{account.id}/balances/{today.year}/{today.month:02d}/{today.day:02d}",
                file_name=f"balances_{uuid.uuid4()}.json",
                file_obj=BytesIO(raw_data),
            )
            context.log.info(f"Successfully uploaded transactions for account {account.id}")


extraction_asset_defs = Definitions(
    assets=[
        gocardless_extract_transactions,
        gocardless_extract_account_details,
        gocardless_extract_balances,
    ]
)
