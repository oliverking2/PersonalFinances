"""Postgres operations for agreements."""

from typing import Any

from sqlalchemy.orm import Session

from src.postgres.gocardless.models import EndUserAgreement


def add_agreement(session: Session, data: dict[str, Any]) -> None:
    """Add a new agreement to the database.

    :param session: SQLAlchemy session for database operations.
    :param data: Dictionary containing agreement data from GoCardless API.
    """
    req = EndUserAgreement(
        id=data["id"],
        created=data["created"],
        institution_id=data["institution_id"],
        max_historical_days=data["max_historical_days"],
        access_valid_for_days=data["access_valid_for_days"],
        access_scope=data["access_scope"],
        accepted=data["accepted"],
        reconfirmation=data["reconfirmation"],
    )

    session.add(req)
    session.commit()


def upsert_agreement(session: Session, data: dict[str, Any]) -> None:
    """Upsert an agreement record in the database.

    Creates a new agreement if it doesn't exist, otherwise updates the existing one.

    :param session: SQLAlchemy session for database operations.
    :param data: Dictionary containing agreement data from GoCardless API.
    """
    req = session.get(EndUserAgreement, data["id"])
    if not req:
        add_agreement(session, data)
    else:
        req.accepted = data["accepted"]
        req.reconfirmation = data["reconfirmation"]
        session.commit()
