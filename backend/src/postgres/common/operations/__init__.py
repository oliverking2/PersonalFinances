"""Operations for common domain models."""

from src.postgres.common.operations.accounts import (
    create_account,
    get_account_by_id,
    get_accounts_by_connection_id,
    update_account,
)
from src.postgres.common.operations.connections import (
    create_connection,
    delete_connection,
    get_connection_by_id,
    get_connection_by_provider_id,
    get_connections_by_user_id,
    update_connection_friendly_name,
    update_connection_status,
)
from src.postgres.common.operations.institutions import (
    create_institution,
    get_institution_by_id,
    list_institutions,
    upsert_institution,
)
from src.postgres.common.operations.jobs import (
    create_job,
    get_job_by_id,
    get_jobs_by_user,
    get_latest_job_for_entity,
    update_job_status,
)

__all__ = [
    "create_account",
    "create_connection",
    "create_institution",
    "create_job",
    "delete_connection",
    "get_account_by_id",
    "get_accounts_by_connection_id",
    "get_connection_by_id",
    "get_connection_by_provider_id",
    "get_connections_by_user_id",
    "get_institution_by_id",
    "get_job_by_id",
    "get_jobs_by_user",
    "get_latest_job_for_entity",
    "list_institutions",
    "update_account",
    "update_connection_friendly_name",
    "update_connection_status",
    "update_job_status",
    "upsert_institution",
]
