"""GoCardless Dagster Background Jobs."""

from dagster import Definitions, OpExecutionContext, ScheduleDefinition, job, op

from src.orchestration.resources import PostgresDatabase
from src.postgres.gocardless.operations.requisitions import (
    create_new_requisition_link,
    fetch_requisition_links,
    update_requisition_record,
)
from src.providers.gocardless.api.core import GoCardlessCredentials


@op(
    name="check_connections_still_valid",
    description="Check that the connections are still valid.",
    required_resource_keys={"postgres_database", "gocardless_api"},
)
def generate_new_links_for_expired_accounts(context: OpExecutionContext) -> None:
    """Check that the connections are still valid."""
    db: PostgresDatabase = context.resources.postgres_database
    creds: GoCardlessCredentials = context.resources.gocardless_api

    with db.get_session() as session:
        links = fetch_requisition_links(session)
        context.log.info(f"Found {len(links)} requisition links")

        for link in links:
            if link.dg_account_expired:
                continue

            context.log.info(f"Checking account status' for requisition ID: {link.id}")
            for account in link.accounts:
                status = account.status
                context.log.info(f"Account {account.id} has status: {status}")

                if status == "EXPIRED":
                    # update existing record
                    update_requisition_record(session, link.id, {"dg_account_expired": True})

                    # create new link with same friendly_name
                    context.log.info(f"Creating new requisition link for account {account.id}")
                    create_new_requisition_link(
                        session, creds, link.institution_id, link.friendly_name
                    )


@job(name="gocardless_daily_jobs", description="Daily processes to run for GoCardless.")
def daily_gocardless_job() -> None:
    """Daily processes to run for GoCardless."""
    generate_new_links_for_expired_accounts()


daily_gocardless_job_schedule = ScheduleDefinition(
    job=daily_gocardless_job,
    cron_schedule="0 3 * * *",
    execution_timezone="Europe/London",
    tags={"schedule_name": "weekly_etl"},
)

daily_job_defs = Definitions(schedules=[daily_gocardless_job_schedule], jobs=[daily_gocardless_job])
