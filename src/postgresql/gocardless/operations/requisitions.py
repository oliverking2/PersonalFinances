"""GoCardless Requisition database operations."""

import logging
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from src.postgresql.gocardless.models import RequisitionLink

logger = logging.getLogger(__name__)


def fetch_requisition_links(session: Session) -> List[RequisitionLink]:
    """Fetch all requisition links from the database, ordered by creation date.

    Retrieves all RequisitionLink records from the database and orders them
    by creation date in descending order (newest first).

    :param session: SQLAlchemy session for database operations
    :returns: A list of RequisitionLink objects ordered by creation date (newest first)
    :raises: Exception if there's an error querying the database
    """
    logger.info("Fetching requisition links from database")
    try:
        links = session.query(RequisitionLink).order_by(RequisitionLink.created.desc()).all()
        logger.info(f"Retrieved {len(links)} requisition links")
        return links
    except Exception as e:
        logger.error(f"Error fetching requisition links: {e!s}")
        raise


def fetch_all_requisition_ids(session: Session) -> List[str]:
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


def add_requisition_link(session: Session, data: Dict[str, Any]) -> None:
    """Add a new requisition link to the database.

    Creates a new RequisitionLink object from the provided data and adds it to the database.
    The data typically comes from a successful response from the GoCardless API when
    creating a new bank connection.

    :param session: Database session.
    :param data: Dictionary containing requisition link data from GoCardless API
    :type data: Dict[str, Any]
    :raises: Exception if there's an error adding the requisition link to the database
    :returns: None
    """
    logger.info(f"Adding new requisition link for institution: {data['institution_id']}")
    req = RequisitionLink(
        id=data["id"],
        created=datetime.fromisoformat(data["created"].replace("Z", "+00:00")),
        updated=datetime.fromisoformat(data["created"].replace("Z", "+00:00")),
        redirect=data["redirect"],
        status=data["status"],
        institution_id=data["institution_id"],
        agreement=data["agreement"],
        reference=data["reference"],
        link=data["link"],
        ssn=data["ssn"],
        account_selection=data["account_selection"],
        redirect_immediate=data["redirect_immediate"],
    )

    try:
        session.add(req)
        session.commit()
        logger.info(f"Successfully added requisition link with ID: {data['id']}")
    except Exception as e:
        logger.error(f"Failed to add requisition link: {e!s}")
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


def upsert_requisition_status(session: Session, req_id: str, new_status: str) -> RequisitionLink:
    """Update or create the RequisitionLink record in the database.

    Upserts the RequisitionLink entry for the given requisition ID with the latest status.

    :param session: SQLAlchemy session for database operations
    :param req_id: The requisition ID to upsert.
    :param new_status: The updated status value from GoCardless.
    :returns: The upserted RequisitionLink object.
    :raises: Exception if there's an error updating the database
    """
    logger.info(f"Upserting requisition link with ID: {req_id}, new status: {new_status}")
    try:
        req = session.get(RequisitionLink, req_id)
        if not req:
            logger.info(f"Creating new requisition link for ID: {req_id}")
            req = RequisitionLink(id=req_id, status=new_status)
            session.add(req)
        else:
            logger.info(
                f"Updating existing requisition link status from {req.status} to {new_status}"
            )
            req.status = new_status
        session.commit()
        logger.debug(f"Successfully upserted requisition link with ID: {req_id}")
        return req
    except Exception as e:
        logger.error(f"Failed to upsert requisition link with ID {req_id}: {e!s}")
        raise
