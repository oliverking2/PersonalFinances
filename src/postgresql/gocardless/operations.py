"""GoCardless database operations."""

import logging
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from src.postgresql.gocardless.models import RequisitionLink

logger = logging.getLogger(__name__)


def get_all_requisition_ids(session: Session) -> List[str]:
    """Get all requisition IDs from the database.

    :param session: SQLAlchemy session for database operations
    :returns: List of requisition IDs as strings
    :raises: SQLAlchemy exceptions for database errors
    """
    logger.debug("Fetching all requisition IDs from database")
    try:
        ids = session.query(RequisitionLink.id).all()
        requisition_ids = [id_tuple[0] for id_tuple in ids]
        logger.info(f"Retrieved {len(requisition_ids)} requisition IDs")
        return requisition_ids
    except Exception as e:
        logger.error(f"Failed to fetch requisition IDs: {e}")
        raise


def update_requisition_record(session: Session, requisition_id: str, data: Dict[str, Any]) -> bool:
    """Update a requisition record with new data from the API.

    :param session: SQLAlchemy session for database operations
    :param requisition_id: The requisition ID to update
    :param data: Dictionary containing the updated data fields
    :returns: True if update was successful, False if record not found
    :raises: SQLAlchemy exceptions for database errors
    """
    logger.debug(f"Updating requisition record {requisition_id}")
    try:
        obj = session.get(RequisitionLink, requisition_id)
        if not obj:
            logger.warning(f"Requisition record {requisition_id} not found")
            return False

        # Define explicitly which fields can be updated (excluding 'accounts', 'id', and 'created')
        updatable_fields = {
            "redirect",
            "status",
            "institution_id",
            "agreement",
            "reference",
            "link",
            "ssn",
            "account_selection",
            "redirect_immediate",
        }

        updated_fields = []
        for key, value in data.items():
            if key in updatable_fields:
                logger.debug(f"Updating field {key} with value: {value}")
                setattr(obj, key, value)
                updated_fields.append(key)
            else:
                logger.warning(f"Field {key} not in allowed updatable fields")

        # Always update the 'updated' column with current datetime
        obj.updated = datetime.now()
        updated_fields.append("updated")

        session.commit()
        logger.info(f"Updated requisition {requisition_id} with fields: {updated_fields}")
        return True
    except Exception as e:
        logger.error(f"Failed to update requisition {requisition_id}: {e}")
        session.rollback()
        raise
