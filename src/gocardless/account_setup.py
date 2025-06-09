"""Programmatic setup of an account."""

from typing import List, Dict, Any

import requests

from src.gocardless.api.auth import GoCardlessCredentials

# status: https://developer.gocardless.com/bank-account-data/statuses


def get_institutions(creds: GoCardlessCredentials) -> List[Dict[str, Any]]:
    """Get a list of available institutions.

    Nationwide: NATIONWIDE_NAIAGB21
    Chase: CHASE_CHASGB2L
    Amex: AMERICAN_EXPRESS_AESUGB21
    """
    headers = {"Authorization": f"Bearer {creds.access_token}"}
    params = {"country": "gb"}
    response = requests.get(
        "https://bankaccountdata.gocardless.com/api/v2/institutions", headers=headers, params=params
    )
    response.raise_for_status()

    return response.json()


def create_link(creds: GoCardlessCredentials, callback: str, institution_id: str) -> Dict[str, Any]:
    """Create a link with GoCardless."""
    headers = {"Authorization": f"Bearer {creds.access_token}"}
    payload = {"redirect": callback, "institution_id": institution_id}
    response = requests.post(
        "https://bankaccountdata.gocardless.com/api/v2/requisitions/", headers=headers, json=payload
    )
    response.raise_for_status()

    return response.json()
