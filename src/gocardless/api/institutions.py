"""Module containing functions for managing institutions with GoCardless."""

from typing import Any

from src.gocardless.api.core import GoCardlessCredentials
from src.utils.logging import setup_dagster_logger

logger = setup_dagster_logger("gocardless_api_institutions")

# status: https://developer.gocardless.com/bank-account-data/statuses


def get_institutions(creds: GoCardlessCredentials) -> list[dict[str, Any]]:
    """Get a list of available institutions.

    Nationwide: NATIONWIDE_NAIAGB21
    Chase: CHASE_CHASGB2L
    Amex: AMERICAN_EXPRESS_AESUGB21
    """
    params = {"country": "gb"}

    resp = creds.make_get_request(
        "https://bankaccountdata.gocardless.com/api/v2/institutions", params=params
    )
    if not isinstance(resp, list):
        raise ValueError("Response from GoCardless not in expected format.")

    return resp


def get_institution_mapping(creds: GoCardlessCredentials) -> dict[str, str]:
    """Get a mapping of institution names to IDs.

    :param creds: GoCardlessCredentials object for authentication
    :returns: A dictionary mapping institution names to IDs
    """
    gocardless_creds = creds
    logger.info("Fetching institution mapping from GoCardless")
    institutions = get_institutions(gocardless_creds)
    logger.debug(f"Retrieved {len(institutions)} institutions")
    return {inst["name"]: inst["id"] for inst in institutions}
