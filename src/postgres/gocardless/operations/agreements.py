"""Postgres operations for agreements."""

from typing import Dict, Any
from sqlalchemy.orm import Session

from src.postgres.gocardless.models import EndUserAgreement


def add_agreement(session: Session, data: Dict[str, Any]) -> None:
    """Add a new agreement to the database."""
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

    try:
        session.add(req)
        session.commit()
    except Exception:
        raise


def upsert_agreement(session: Session, data: Dict[str, Any]) -> None:
    """Upsert an agreement record in the database."""
    req = session.get(EndUserAgreement, data["id"])
    if not req:
        add_agreement(session, data)

    else:
        req.accepted = data["accepted"]
        req.reconfirmation = data["reconfirmation"]
        session.commit()
