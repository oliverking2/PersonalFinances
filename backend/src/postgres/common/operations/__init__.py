"""Operations for common domain models."""

from src.postgres.common.operations.accounts import (
    create_account,
    get_account_by_id,
    get_accounts_by_connection_id,
    update_account_display_name,
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

__all__ = [
    "create_account",
    "create_connection",
    "create_institution",
    "delete_connection",
    "get_account_by_id",
    "get_accounts_by_connection_id",
    "get_connection_by_id",
    "get_connection_by_provider_id",
    "get_connections_by_user_id",
    "get_institution_by_id",
    "list_institutions",
    "update_account_display_name",
    "update_connection_friendly_name",
    "update_connection_status",
    "upsert_institution",
]
