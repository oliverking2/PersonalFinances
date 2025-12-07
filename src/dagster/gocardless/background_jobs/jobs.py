"""GoCardless Dagster Background Jobs."""

from dagster import op, OpExecutionContext

from src.dagster.resources import PostgresDatabase
from src.postgres.gocardless.operations.requisitions import (
    fetch_requisition_links,
    update_requisition_record,
)


@op(
    name="check_connections_still_valid",
    description="Check that the connections are still valid.",
    required_resource_keys={"postgres_database"},
)
def generate_new_links_for_expired_accounts(context: OpExecutionContext) -> None:
    """Check that the connections are still valid."""
    db: PostgresDatabase = context.resources.postgres_database

    with db.get_session() as session:
        links = fetch_requisition_links(session)
        context.log.info(f"Found {len(links)} requisition links")

    for link in links:
        context.log.info(f"Checking account status' for requisition ID: {link.id}")
        for account in link.accounts:
            status = account.status
            context.log.info(f"Account {account.id} has status: {status}")

            if status == "EXPIRED":
                update_requisition_record(session, link.id, {"dg_account_expired": True})
