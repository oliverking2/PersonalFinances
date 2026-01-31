"""Shared helper functions for API endpoints."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.postgres.auth.models import User
from src.postgres.common.models import Account
from src.postgres.common.operations.accounts import get_account_by_id
from src.postgres.common.operations.connections import get_connections_by_user_id


def get_user_account_ids(db: Session, user: User) -> list[UUID]:
    """Get all account IDs for a user.

    :param db: Database session.
    :param user: Authenticated user.
    :returns: List of account UUIDs owned by the user.
    """
    connections = get_connections_by_user_id(db, user.id)
    return [acc.id for conn in connections for acc in conn.accounts]


def verify_user_owns_account(db: Session, account_id: UUID, user: User) -> Account:
    """Verify user owns the account and return it if so.

    :param db: Database session.
    :param account_id: Account UUID to verify.
    :param user: Authenticated user.
    :returns: The Account if user owns it.
    :raises HTTPException: 404 if account not found or not owned by user.
    """
    account = get_account_by_id(db, account_id)
    if not account or account.connection.user_id != user.id:
        raise HTTPException(status_code=404, detail=f"Account not found: {account_id}")
    return account
