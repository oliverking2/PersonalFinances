"""Database operations for GoCardless institutions."""

from typing import Any

from dagster import get_dagster_logger
from sqlalchemy.orm import Session

from src.postgres.gocardless.models import GoCardlessInstitution

logger = get_dagster_logger()


def upsert_institutions(session: Session, institutions: list[dict[str, Any]]) -> int:
    """Upsert GoCardless institutions into gc_institutions.

    :param session: SQLAlchemy session.
    :param institutions: List of institution payloads from GoCardless API.
    :returns: Number of institutions processed.
    """
    if not institutions:
        logger.info("No institutions provided; skipping upsert")
        return 0

    count = 0
    for inst in institutions:
        inst_id = inst["id"]

        existing = session.get(GoCardlessInstitution, inst_id)
        if existing:
            existing.name = inst.get("name", existing.name)
            existing.bic = inst.get("bic")
            existing.logo = inst.get("logo")
            existing.countries = inst.get("countries")
        else:
            obj = GoCardlessInstitution(
                id=inst_id,
                name=inst.get("name", ""),
                bic=inst.get("bic"),
                logo=inst.get("logo"),
                countries=inst.get("countries"),
            )
            session.add(obj)

        count += 1

    session.flush()
    logger.info(f"Upserted {count} institutions into gc_institutions")
    return count
