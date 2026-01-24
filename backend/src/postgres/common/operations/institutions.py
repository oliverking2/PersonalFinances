"""Institution database operations.

This module provides CRUD operations for Institution entities.
"""

import logging

from sqlalchemy import cast
from sqlalchemy.orm import Session
from sqlalchemy.types import String

from src.postgres.common.enums import Provider
from src.postgres.common.models import Institution

logger = logging.getLogger(__name__)


def get_institution_by_id(session: Session, institution_id: str) -> Institution | None:
    """Get an institution by its ID.

    :param session: SQLAlchemy session.
    :param institution_id: Institution's ID (provider-specific, e.g., NATIONWIDE_NAIAGB21).
    :return: Institution if found, None otherwise.
    """
    return session.get(Institution, institution_id)


def list_institutions(
    session: Session,
    provider: Provider | None = None,
    country: str | None = None,
) -> list[Institution]:
    """List institutions with optional filtering.

    :param session: SQLAlchemy session.
    :param provider: Filter by provider (optional).
    :param country: Filter by country code (optional, e.g., 'GB').
    :return: List of matching institutions.
    """
    query = session.query(Institution)

    if provider is not None:
        query = query.filter(Institution.provider == provider.value)

    if country is not None:
        # Use LIKE for portable JSON array search (works in both SQLite and PostgreSQL)
        # This matches the country code as a quoted string within the JSON array
        query = query.filter(cast(Institution.countries, String).like(f'%"{country}"%'))

    return query.order_by(Institution.name).all()


def create_institution(  # noqa: PLR0913
    session: Session,
    institution_id: str,
    provider: Provider,
    name: str,
    logo_url: str | None = None,
    countries: list[str] | None = None,
) -> Institution:
    """Create a new institution.

    :param session: SQLAlchemy session.
    :param institution_id: Provider's institution ID.
    :param provider: Provider enum.
    :param name: Institution name.
    :param logo_url: URL to institution logo (optional).
    :param countries: List of country codes (optional).
    :return: Created Institution entity.
    """
    institution = Institution(
        id=institution_id,
        provider=provider.value,
        name=name,
        logo_url=logo_url,
        countries=countries,
    )
    session.add(institution)
    session.flush()
    logger.info(f"Created institution: id={institution_id}, name={name}")
    return institution


def upsert_institution(  # noqa: PLR0913
    session: Session,
    institution_id: str,
    provider: Provider,
    name: str,
    logo_url: str | None = None,
    countries: list[str] | None = None,
) -> Institution:
    """Create or update an institution.

    :param session: SQLAlchemy session.
    :param institution_id: Provider's institution ID.
    :param provider: Provider enum.
    :param name: Institution name.
    :param logo_url: URL to institution logo (optional).
    :param countries: List of country codes (optional).
    :return: Created or updated Institution entity.
    """
    institution = get_institution_by_id(session, institution_id)

    if institution is None:
        return create_institution(
            session,
            institution_id=institution_id,
            provider=provider,
            name=name,
            logo_url=logo_url,
            countries=countries,
        )

    # Update existing
    institution.name = name
    institution.logo_url = logo_url
    institution.countries = countries
    session.flush()
    logger.info(f"Updated institution: id={institution_id}, name={name}")
    return institution
