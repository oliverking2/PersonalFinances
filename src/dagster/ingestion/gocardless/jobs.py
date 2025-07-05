"""GoCardless Dagster Jobs."""

from dagster import job

from src.dagster.ingestion.gocardless.ops import fetch_requisition_ids, refresh_and_update_record
from src.dagster.ingestion.gocardless.resources import postgres_db_session_resource


@job(
    name="requisition_sync_job",
    resource_defs={
        "postgres_db": postgres_db_session_resource,
    },
)
def requisition_sync_job() -> None:
    """Fetch all requisition IDs and refresh each record with retries."""
    fetch_requisition_ids().map(refresh_and_update_record)
