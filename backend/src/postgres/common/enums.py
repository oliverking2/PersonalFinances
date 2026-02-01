"""Shared enums for common domain models.

Defines provider-agnostic status enums used across connections and accounts.
"""

from enum import StrEnum


class Provider(StrEnum):
    """Supported data providers."""

    GOCARDLESS = "gocardless"
    TRADING212 = "trading212"
    VANGUARD = "vanguard"


class AccountType(StrEnum):
    """Account type classification.

    - BANK: Traditional bank accounts (GoCardless)
    - INVESTMENT: Investment portfolios (Vanguard funds)
    - TRADING: Trading accounts (Trading212 ISA/GIA)
    """

    BANK = "bank"
    INVESTMENT = "investment"
    TRADING = "trading"


class ConnectionStatus(StrEnum):
    """Normalised connection status.

    Maps provider-specific statuses to a common set:
    - pending: Connection in progress (GoCardless: CR, GA, SA)
    - active: Connection established and working (GoCardless: LN)
    - expired: Connection expired, needs reauthorisation (GoCardless: EX)
    - error: Connection failed or rejected (GoCardless: RJ, UA, SU)
    """

    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    ERROR = "error"


class AccountStatus(StrEnum):
    """Normalised account status.

    Maps provider-specific statuses to a common set:
    - active: Account is accessible (GoCardless: READY)
    - inactive: Account unavailable (GoCardless: EXPIRED, SUSPENDED, null)
    """

    ACTIVE = "active"
    INACTIVE = "inactive"


class AccountCategory(StrEnum):
    """User-selectable account category.

    Provides additional categorisation for accounts beyond the provider-determined
    account_type. Users can classify their accounts for better organisation.
    """

    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_ACCOUNT = "bank_account"
    INVESTMENT_ACCOUNT = "investment_account"


# GoCardless status mapping helpers
_GC_REQUISITION_STATUS_MAP: dict[str, ConnectionStatus] = {
    "CR": ConnectionStatus.PENDING,  # Created
    "GA": ConnectionStatus.PENDING,  # Granting Access
    "SA": ConnectionStatus.PENDING,  # Selecting Accounts
    "LN": ConnectionStatus.ACTIVE,  # Linked
    "EX": ConnectionStatus.EXPIRED,  # Expired
    "RJ": ConnectionStatus.ERROR,  # Rejected
    "UA": ConnectionStatus.ERROR,  # User Abandoned
    "SU": ConnectionStatus.ERROR,  # Suspended
}

_GC_ACCOUNT_STATUS_MAP: dict[str | None, AccountStatus] = {
    "READY": AccountStatus.ACTIVE,
    "EXPIRED": AccountStatus.INACTIVE,
    "SUSPENDED": AccountStatus.INACTIVE,
    None: AccountStatus.INACTIVE,
}


def map_gc_requisition_status(gc_status: str) -> ConnectionStatus:
    """Map GoCardless requisition status to normalised ConnectionStatus.

    :param gc_status: GoCardless requisition status code (e.g., 'LN', 'EX').
    :returns: Normalised ConnectionStatus.
    """
    return _GC_REQUISITION_STATUS_MAP.get(gc_status, ConnectionStatus.ERROR)


def map_gc_account_status(gc_status: str | None) -> AccountStatus:
    """Map GoCardless account status to normalised AccountStatus.

    :param gc_status: GoCardless account status (e.g., 'READY', 'EXPIRED').
    :returns: Normalised AccountStatus.
    """
    return _GC_ACCOUNT_STATUS_MAP.get(gc_status, AccountStatus.INACTIVE)


class JobType(StrEnum):
    """Type of background job.

    - SYNC: Data synchronisation job (fetch from provider, update local data)
    - EXPORT: Data export job (generate reports, CSV files, etc.)
    """

    SYNC = "sync"
    EXPORT = "export"


class JobStatus(StrEnum):
    """Background job execution status.

    - PENDING: Job created but not yet started
    - RUNNING: Job is currently executing
    - COMPLETED: Job finished successfully
    - FAILED: Job failed with an error
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RecurringFrequency(StrEnum):
    """Frequency of recurring transactions.

    - WEEKLY: Every 7 days
    - FORTNIGHTLY: Every 14 days
    - MONTHLY: Once per month
    - QUARTERLY: Every 3 months
    - ANNUAL: Once per year
    - IRREGULAR: Variable frequency that doesn't fit standard patterns
    """

    WEEKLY = "weekly"
    FORTNIGHTLY = "fortnightly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    IRREGULAR = "irregular"


class RecurringStatus(StrEnum):
    """Status of a recurring payment pattern.

    - PENDING: Auto-detected, awaiting user acceptance
    - ACTIVE: User-confirmed or manually created, actively tracked
    - PAUSED: User temporarily paused (e.g., subscription on hold)
    - CANCELLED: Pattern ended, no longer recurring
    """

    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class RecurringSource(StrEnum):
    """Source of how a recurring pattern was created.

    - DETECTED: Created by automatic detection from transaction history
    - MANUAL: Created manually by the user
    """

    DETECTED = "detected"
    MANUAL = "manual"


class RecurringDirection(StrEnum):
    """Direction of a recurring transaction.

    - EXPENSE: Outgoing payment (subscriptions, bills)
    - INCOME: Incoming payment (salary, regular transfers)
    """

    EXPENSE = "expense"
    INCOME = "income"


class BudgetPeriod(StrEnum):
    """Budget time period.

    - WEEKLY: Budget resets each ISO week (Monday-Sunday)
    - MONTHLY: Budget resets each calendar month
    - QUARTERLY: Budget resets each quarter (Q1: Jan-Mar, Q2: Apr-Jun, etc.)
    - ANNUAL: Budget resets each calendar year
    """

    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class GoalStatus(StrEnum):
    """Status of a savings goal.

    - ACTIVE: Goal is being tracked
    - PAUSED: Goal is temporarily paused
    - COMPLETED: Goal has been achieved
    - CANCELLED: Goal was abandoned
    """

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class GoalTrackingMode(StrEnum):
    """Tracking mode for savings goals.

    - MANUAL: User adds contributions manually
    - BALANCE: Mirrors linked account balance directly
    - DELTA: Progress = current balance - starting balance (savings since goal creation)
    - TARGET_BALANCE: Goal completes when account reaches target balance
    """

    MANUAL = "manual"
    BALANCE = "balance"
    DELTA = "delta"
    TARGET_BALANCE = "target_balance"


class TransactionStatus(StrEnum):
    """Status of a transaction in the unified table.

    - ACTIVE: Normal transaction, visible in all views
    - RECONCILED: Pending transaction replaced by booked version, kept for audit
    """

    ACTIVE = "active"
    RECONCILED = "reconciled"


class NotificationType(StrEnum):
    """Type of in-app notification.

    Budget notifications:
    - BUDGET_WARNING: Budget approaching limit (default 80%)
    - BUDGET_EXCEEDED: Budget has been exceeded

    Export notifications:
    - EXPORT_COMPLETE: Data export finished successfully
    - EXPORT_FAILED: Data export failed with an error

    Sync notifications (bank data):
    - SYNC_COMPLETE: Bank data sync finished successfully
    - SYNC_FAILED: Bank data sync failed with an error

    Analytics refresh notifications (dbt):
    - ANALYTICS_REFRESH_COMPLETE: Analytics refresh finished successfully
    - ANALYTICS_REFRESH_FAILED: Analytics refresh failed with an error
    """

    BUDGET_WARNING = "budget_warning"
    BUDGET_EXCEEDED = "budget_exceeded"
    EXPORT_COMPLETE = "export_complete"
    EXPORT_FAILED = "export_failed"
    SYNC_COMPLETE = "sync_complete"
    SYNC_FAILED = "sync_failed"
    ANALYTICS_REFRESH_COMPLETE = "analytics_refresh_complete"
    ANALYTICS_REFRESH_FAILED = "analytics_refresh_failed"


class ManualAssetType(StrEnum):
    """Type of manually tracked asset or liability.

    Liabilities (typically negative impact on net worth):
    - STUDENT_LOAN: Student loan debt
    - MORTGAGE: Mortgage on property

    Assets (typically positive impact on net worth):
    - VEHICLE: Cars, motorcycles, etc.
    - PROPERTY: Real estate, land
    - SAVINGS_ACCOUNT: Manual savings accounts not connected via banking API
    - PENSION: Pension funds, retirement accounts
    - INVESTMENTS: Investment accounts (stocks, funds, ISAs)
    - CRYPTO: Cryptocurrency holdings

    Other:
    - OTHER_ASSET: Any other asset type
    - OTHER_LIABILITY: Any other liability type
    """

    STUDENT_LOAN = "student_loan"
    MORTGAGE = "mortgage"
    VEHICLE = "vehicle"
    PROPERTY = "property"
    SAVINGS_ACCOUNT = "savings_account"
    PENSION = "pension"
    INVESTMENTS = "investments"
    CRYPTO = "crypto"
    OTHER_ASSET = "other_asset"
    OTHER_LIABILITY = "other_liability"


# Default liability status for each asset type
_MANUAL_ASSET_TYPE_IS_LIABILITY: dict[ManualAssetType, bool] = {
    ManualAssetType.STUDENT_LOAN: True,
    ManualAssetType.MORTGAGE: True,
    ManualAssetType.VEHICLE: False,
    ManualAssetType.PROPERTY: False,
    ManualAssetType.SAVINGS_ACCOUNT: False,
    ManualAssetType.PENSION: False,
    ManualAssetType.INVESTMENTS: False,
    ManualAssetType.CRYPTO: False,
    ManualAssetType.OTHER_ASSET: False,
    ManualAssetType.OTHER_LIABILITY: True,
}


def get_default_is_liability(asset_type: ManualAssetType) -> bool:
    """Get the default is_liability value for a manual asset type.

    :param asset_type: The manual asset type.
    :returns: True if this type is typically a liability, False if an asset.
    """
    return _MANUAL_ASSET_TYPE_IS_LIABILITY.get(asset_type, False)
