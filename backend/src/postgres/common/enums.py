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
