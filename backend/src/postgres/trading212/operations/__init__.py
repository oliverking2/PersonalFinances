"""Trading 212 database operations."""

from src.postgres.trading212.operations.api_keys import (
    create_api_key,
    delete_api_key,
    get_active_api_keys,
    get_all_api_keys_for_sync,
    get_api_key_by_id,
    get_api_keys_by_user,
    update_api_key_status,
)
from src.postgres.trading212.operations.cash_balances import (
    get_latest_cash_balance,
    upsert_cash_balance,
)
from src.postgres.trading212.operations.history import (
    get_dividends_for_api_key,
    get_orders_for_api_key,
    get_transactions_for_api_key,
    upsert_dividend,
    upsert_order,
    upsert_transaction,
)

__all__ = [
    "create_api_key",
    "delete_api_key",
    "get_active_api_keys",
    "get_all_api_keys_for_sync",
    "get_api_key_by_id",
    "get_api_keys_by_user",
    "get_dividends_for_api_key",
    "get_latest_cash_balance",
    "get_orders_for_api_key",
    "get_transactions_for_api_key",
    "update_api_key_status",
    "upsert_cash_balance",
    "upsert_dividend",
    "upsert_order",
    "upsert_transaction",
]
