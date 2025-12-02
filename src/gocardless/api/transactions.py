"""Module for using the GoCardless Transactions API."""

from typing import Dict, Any


from src.gocardless.api.core import GoCardlessCredentials
from src.utils.logging import get_logger

logger = get_logger("gocardless_api_transactions")


def get_transaction_data_for_account(
    creds: GoCardlessCredentials, account_id: str, date_from: str, date_to: str
) -> Dict[str, Any]:
    """Fetch transaction data from the GoCardless API for the specified account and date range.

    The function communicates with the GoCardless API to retrieve transaction details of the given
    account within the defined date range. Returns a list of transaction records containing details
    such as date, amount, and other related metadata. It raises an exception if the HTTP request
    fails.

    :param creds: GoCardlessCredentials object for authentication
    :param account_id: The unique identifier of the bank account
    :param date_from: The start date (inclusive) of the transaction range, in YYYY-MM-DD format
    :param date_to: The end date (inclusive) of the transaction range, in YYYY-MM-DD format
    :returns: A list of transaction records as dictionaries

    """
    logger.info("Fetching transaction data from GoCardless")
    url = f"https://bankaccountdata.gocardless.com/api/v2/accounts/{account_id}/transactions"
    params = {"date_from": date_from, "date_to": date_to}

    return creds.make_get_request(url, params)


if __name__ == "__main__":
    creds = GoCardlessCredentials()
    print(
        get_transaction_data_for_account(
            creds, "73ed675f-12fe-4d85-88d3-d439976ec662", "2025-11-01", "2025-11-30"
        )
    )
