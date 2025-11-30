"""GoCardless Dagster Resources."""

from dagster import resource, InitResourceContext, get_dagster_logger

from src.gocardless.api.auth import GoCardlessCredentials


logger = get_dagster_logger()


@resource
def gocardless_api_resource(_context: InitResourceContext) -> GoCardlessCredentials:
    """Create a GoCardlessCredentials object for use in other resources and ops."""
    return GoCardlessCredentials()
