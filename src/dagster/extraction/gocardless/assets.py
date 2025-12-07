"""GoCardless Dagster Assets."""

import json
import os
from datetime import date
from typing import TYPE_CHECKING
import uuid
from io import BytesIO

from dagster import (
    asset,
    AutomationCondition,
    AssetExecutionContext,
    AssetsDefinition,
    Definitions,
)
from dateutil.relativedelta import relativedelta
from mypy_boto3_s3 import S3Client

from src.aws.s3 import upload_bytes_to_s3
from src.dagster.resources import PostgresDatabase
from src.gocardless.api.core import GoCardlessCredentials
from src.gocardless.api.transactions import get_transaction_data_for_account

from src.postgres.gocardless.operations.bank_accounts import (
    get_transaction_watermark,
    get_active_accounts,
    update_transaction_watermark,
)
from src.postgres.utils import create_session
from src.utils.definitions import gocardless_database_url

if TYPE_CHECKING:
    from src.postgres.gocardless.models import BankAccount


def create_extract_transaction_asset(account: "BankAccount") -> AssetsDefinition:
    """Create extract transaction assets."""

    @asset(
        name=f"extract_transactions_account_{account.id}",
        description=f"Extract transactions for account {account.requisition.institution_id} {account.name}",
        required_resource_keys={"s3", "gocardless_api", "postgres_database"},
        automation_condition=AutomationCondition.on_cron("0 4 * * *"),
    )
    def _asset(context: AssetExecutionContext) -> None:
        """Extract transactions from account 1."""
        creds: GoCardlessCredentials = context.resources.gocardless_api
        s3: S3Client = context.resources.s3
        postgres_database: PostgresDatabase = context.resources.postgres_database

        today = date.today()

        with postgres_database.get_session() as session:
            watermark = get_transaction_watermark(session, account.id)

        context.log.info(f"Watermark for account {account.id}: {watermark}")
        date_start = today + relativedelta(days=-90) if watermark is None else watermark

        # go a few days further back to add some overlap incase any data was missed
        date_start += relativedelta(days=-3)

        context.log.info(
            f"Extracting transactions for account {account.id} from {date_start} to {today}"
        )

        # get data from watermark till today
        raw_transactions = get_transaction_data_for_account(
            creds, account.id, date_start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
        )

        raw_data = json.dumps(raw_transactions).encode("utf-8")

        # Upload to S3
        upload_bytes_to_s3(
            s3_client=s3,
            bucket_name=os.environ["S3_BUCKET_NAME"],
            prefix=f"extracts/gocardless/{account.id}/{today.year}/{today.month:02d}/{today.day:02d}",
            file_name=f"transactions_{uuid.uuid4()}.json",
            file_obj=BytesIO(raw_data),
        )
        context.log.info(f"Successfully uploaded transactions for account {account.id}")

        with postgres_database.get_session() as session:
            update_transaction_watermark(session, account.id, today)

        context.log.info(
            f"Successfully updated watermark for account {account.id} with date {today}"
        )

    return _asset


db_session = create_session(gocardless_database_url())

extraction_asset_defs = Definitions(
    assets=[
        create_extract_transaction_asset(account) for account in get_active_accounts(db_session)
    ]
)
