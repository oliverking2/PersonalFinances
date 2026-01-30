"""Maintenance Dagster jobs.

Scheduled jobs for database cleanup and maintenance tasks.
"""

from dagster import OpExecutionContext, ScheduleDefinition, job, op

from src.orchestration.resources import PostgresDatabase
from src.postgres.common.operations.notifications import delete_old_notifications


@op(
    name="cleanup_old_notifications",
    description="Delete read notifications older than 30 days.",
    required_resource_keys={"postgres_database"},
)
def cleanup_old_notifications_op(context: OpExecutionContext) -> None:
    """Delete read notifications older than 30 days."""
    db: PostgresDatabase = context.resources.postgres_database

    with db.get_session() as session:
        deleted_count = delete_old_notifications(session, days=30)
        context.log.info(f"Deleted {deleted_count} old notifications")


@job(
    name="maintenance_cleanup_job",
    description="Daily maintenance job for database cleanup tasks.",
)
def maintenance_cleanup_job() -> None:
    """Daily maintenance job for database cleanup tasks."""
    cleanup_old_notifications_op()


# Run daily at 4am London time (after GoCardless daily jobs at 3am)
maintenance_cleanup_schedule = ScheduleDefinition(
    job=maintenance_cleanup_job,
    cron_schedule="0 4 * * *",
    execution_timezone="Europe/London",
    tags={"schedule_name": "daily_maintenance"},
)
