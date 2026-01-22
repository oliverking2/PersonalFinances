"""Gocardless agreements API.

This isn't possible with the current configuration of my account.
"""

from typing import Any

from src.providers.gocardless.api.core import GoCardlessCredentials


def get_all_agreements(creds: GoCardlessCredentials) -> list[dict[str, Any]]:
    """Get all agreements from GoCardless."""
    agreements = creds.make_get_request(
        "https://bankaccountdata.gocardless.com/api/v2/agreements/enduser"
    )
    if not isinstance(agreements, dict):
        raise ValueError("Response from GoCardless not in expected format.")
    return agreements["results"]


def delete_agreement(creds: GoCardlessCredentials, agreement_id: str) -> dict[str, Any]:
    """Delete an agreement from GoCardless."""
    return creds.make_delete_request(
        f"https://bankaccountdata.gocardless.com/api/v2/agreements/enduser/{agreement_id}"
    )


def accept_agreement(creds: GoCardlessCredentials, agreement_id: str) -> dict[str, Any]:
    """Accept an agreement from GoCardless."""
    return creds.make_put_request(
        f"https://bankaccountdata.gocardless.com/api/v2/agreements/enduser/{agreement_id}/accept"
    )


if __name__ == "__main__":
    creds = GoCardlessCredentials()
    accept_agreement(creds, "0e93e1f3-e6d0-45fb-b0f1-158bd3754995")
