"""Sync operations for keeping unified tables in sync with provider tables.

This module re-exports sync operations from provider-specific modules
for backward compatibility.

Provider-specific modules:
    - sync_gocardless: GoCardless sync operations
    - sync_trading212: Trading 212 sync operations

New code should import directly from the provider-specific modules.
"""

# GoCardless exports
from src.postgres.common.operations.sync_gocardless import (
    mark_missing_accounts_inactive,
    sync_all_gocardless_accounts,
    sync_all_gocardless_connections,
    sync_all_gocardless_institutions,
    sync_all_gocardless_transactions,
    sync_gocardless_account,
    sync_gocardless_connection,
    sync_gocardless_institution,
    sync_gocardless_transaction,
)

# Trading 212 exports
from src.postgres.common.operations.sync_trading212 import (
    ensure_trading212_institution,
    sync_all_trading212_accounts,
    sync_all_trading212_connections,
    sync_all_trading212_transactions,
    sync_trading212_account,
    sync_trading212_cash_transaction,
    sync_trading212_connection,
    sync_trading212_dividend_transaction,
    sync_trading212_order_transaction,
)

__all__ = [
    "ensure_trading212_institution",
    "mark_missing_accounts_inactive",
    "sync_all_gocardless_accounts",
    "sync_all_gocardless_connections",
    "sync_all_gocardless_institutions",
    "sync_all_gocardless_transactions",
    "sync_all_trading212_accounts",
    "sync_all_trading212_connections",
    "sync_all_trading212_transactions",
    "sync_gocardless_account",
    "sync_gocardless_connection",
    "sync_gocardless_institution",
    "sync_gocardless_transaction",
    "sync_trading212_account",
    "sync_trading212_cash_transaction",
    "sync_trading212_connection",
    "sync_trading212_dividend_transaction",
    "sync_trading212_order_transaction",
]
