"""GoCardless Dagster Ops."""

from typing import Iterator

from dagster import op, RetryPolicy, DynamicOut, DynamicOutput, OpExecutionContext

from src.mysql.gocardless.operations import get_all_requisition_ids, update_requisition_record
from src.gocardless.api.requisition import fetch_requisition_data_by_id
from src.gocardless.api.auth import GoCardlessCredentials


@op(required_resource_keys={"mysql_db"}, out=DynamicOut())
def fetch_requisition_ids(context: OpExecutionContext) -> Iterator[DynamicOutput[str]]:
    """Fetch all requisition_link IDs needing update.

    :param context: Dagster operation execution context
    :returns: Iterator of DynamicOutput containing requisition ID strings
    :raises: Database exceptions if query fails
    """
    session = context.resources.mysql_db
    id_list = get_all_requisition_ids(session)
    context.log.info(f"Fetched {len(id_list)} requisition IDs to refresh")
    for rc_id in id_list:
        yield DynamicOutput(
            value=rc_id, mapping_key=str(rc_id).replace("-", "")
        )  # unique string per element


@op(
    required_resource_keys={"mysql_db"},
    retry_policy=RetryPolicy(max_retries=3, delay=10),
)
def refresh_and_update_record(context: OpExecutionContext, rc_id: str) -> None:
    """Refresh and update a RequisitionLink record.

    Calls GoCardless API to fetch fresh data and updates the database record.
    Includes automatic retry policy for resilience.

    :param context: Dagster operation execution context
    :param rc_id: Requisition ID to refresh and update
    :raises: API exceptions if GoCardless request fails
    :raises: Database exceptions if update fails
    """
    context.log.info(f"Refreshing requisition {rc_id}")

    # Get credentials and fetch data from API
    creds = GoCardlessCredentials()
    try:
        data = fetch_requisition_data_by_id(creds, rc_id)
    except Exception as e:
        context.log.error(f"Failed to fetch data for requisition {rc_id}: {e}")
        raise

    if not data:
        context.log.error(f"No data returned for requisition {rc_id}")
        return

    # Update database record
    session = context.resources.mysql_db
    success = update_requisition_record(session, rc_id, data)

    if success:
        context.log.info(f"Updated requisition {rc_id}")
    else:
        context.log.error(f"Requisition {rc_id} not found in DB")
