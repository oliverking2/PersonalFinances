"""GoCardless Dagster Ops."""

from typing import Iterator

from dagster import op, RetryPolicy, DynamicOut, DynamicOutput, OpExecutionContext

from src.mysql.gocardless import RequisitionLink


@op(required_resource_keys={"mysql_db"}, out=DynamicOut())
def fetch_requisition_ids(context: OpExecutionContext) -> Iterator[DynamicOutput[int]]:
    """Fetch all requisition_link IDs needing update.

    Returns list of integers.
    """
    session = context.resources.mysql_db.session
    ids = session.query(RequisitionLink.id).all()
    id_list = [i[0] for i in ids]
    context.log.info(f"Fetched {len(id_list)} requisition IDs to refresh")
    for rc_id in ids:
        yield DynamicOutput(value=rc_id, mapping_key=str(rc_id))  # unique string per element


@op(
    required_resource_keys={"gocardless_api", "mysql_db"},
    retry_policy=RetryPolicy(max_retries=3, delay=10),
)
def refresh_and_update_record(context: OpExecutionContext, rc_id: int) -> None:
    """Refresh and Update a RequisitionLink record.

    - Call GoCardless API to refresh (with token management)
    - Update ORM object and commit
    """
    context.log.info(f"Refreshing requisition {rc_id}")
    client = context.resources.gocardless_api
    data = client.fetch_requisition(rc_id)
    if not data:
        context.log.error(f"No data returned for requisition {rc_id}")
        return

    session = context.resources.mysql_db
    obj = session.get(RequisitionLink, rc_id)
    if not obj:
        context.log.error(f"Requisition {rc_id} not found in DB")
        return

    # Update fields dynamically
    for key, value in data.items():
        if hasattr(obj, key):
            setattr(obj, key, value)

    session.commit()
    context.log.info(f"Updated requisition {rc_id}")
