"""GoCardless Dagster Assets."""

import json
import tempfile
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING
import uuid

from dagster import (
    asset,
    AutomationCondition,
    AssetExecutionContext,
    AssetsDefinition,
    EnvVar,
    Definitions,
)
from dateutil.relativedelta import relativedelta

from src.aws.s3 import upload_file_to_s3
from src.gocardless.api.transactions import get_transaction_data_for_account

from src.postgres.gocardless.operations.bank_accounts import (
    get_transaction_watermark,
    get_active_accounts,
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
        creds = context.resources.gocardless_api
        s3 = context.resources.s3
        postgres_database = context.resources.postgres_database

        today = date.today()

        watermark = get_transaction_watermark(postgres_database, account.id)
        date_start = today + relativedelta(days=-90) if watermark is None else watermark

        # go a few days further back to add some overlap incase any data was missed
        date_start += relativedelta(days=-3)

        # get data from watermark till today
        raw_transactions = get_transaction_data_for_account(
            creds, account.id, date_start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=True) as temp_file:
            json.dump(raw_transactions, temp_file)

            # Use the temporary file path
            temp_file_path = Path(temp_file.name)

            # Upload to S3
            upload_file_to_s3(
                s3_client=s3,
                bucket_name=EnvVar("S3_BUCKET_NAME"),
                prefix=f"extracts/gocardless/{account.id}/{today.year}/{today.month:02d}/{today.day:02d}",
                file_name=f"transactions_{uuid.uuid4()}.json",
                file_path=temp_file_path,
            )

    return _asset


db_session = create_session(gocardless_database_url())

extraction_asset_defs = Definitions(
    assets=[
        create_extract_transaction_asset(account) for account in get_active_accounts(db_session)
    ]
)
