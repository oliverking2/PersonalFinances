"""Connections Setup Page for managing bank connections via GoCardless API.

This module provides a Streamlit interface for users to:
1. View existing bank connections
2. Create new bank connections
3. Authorize bank connections
4. Delete bank connections

The page interacts with the GoCardless API to manage requisition links and
stores connection data in a MySQL database.
"""

import time
from typing import Dict

import requests
import streamlit as st
from sqlalchemy.orm import Session
from streamlit.runtime.state import QueryParamsProxy

from src.gocardless.api.account import fetch_account_data_by_id
from src.gocardless.api.requisition import (
    fetch_requisition_data_by_id,
    delete_requisition_data_by_id,
)
from src.postgres.gocardless.models import RequisitionLink
from src.postgres.gocardless.operations.bank_accounts import upsert_bank_accounts
from src.postgres.gocardless.operations.requisitions import (
    add_requisition_link,
    fetch_requisition_links,
    upsert_requisition_status,
)
from src.streamlit.utils import get_gocardless_creds, get_gocardless_session
from src.gocardless.account_setup import get_institutions, create_link

# Configure logging

from src.utils.logging import get_logger

logger = get_logger("connections_page")

# page config
st.set_page_config(page_title="Connections", layout="wide")
logger.info("Connections page initialized")

# ─── Load connections from DB ─────────────────────────────────────────────────
logger.info("Connecting to MySQL database")
session: Session = get_gocardless_session()

logger.info("Retrieving GoCardless credentials")
gocardless_creds = get_gocardless_creds()


# 2-letter → full status name
STATUS_NAMES = {
    "CR": "Created",
    "GC": "Giving Consent",
    "UA": "Undergoing Authentication",
    "RJ": "Rejected",
    "SA": "Selecting Accounts",
    "GA": "Granting Access",
    "LN": "Linked",
    "EX": "Expired",
}

# 2-letter → colour emoji
STATUS_EMOJIS = {
    "CR": "🔵",  # blue
    "GC": "🟠",  # orange
    "UA": "🟠",  # orange
    "RJ": "🔴",  # red
    "SA": "🔵",  # blue
    "GA": "🔵",  # blue
    "LN": "🟢",  # green
    "EX": "🔴",  # red
}


@st.cache_data
def get_institution_mapping() -> Dict[str, str]:
    """Fetch and cache a mapping of institution names to their IDs from GoCardless.

    This function retrieves all available banking institutions from the GoCardless API
    and creates a dictionary mapping institution names to their unique identifiers.
    The result is cached by Streamlit to improve performance on subsequent calls.

    :returns: A dictionary mapping institution names to their IDs
    :rtype: Dict[str, str]
    :raises: Exception if the API call to GoCardless fails
    """
    logger.info("Fetching institution mapping from GoCardless")
    institutions = get_institutions(gocardless_creds)
    logger.debug(f"Retrieved {len(institutions)} institutions")
    return {inst["name"]: inst["id"] for inst in institutions}


@st.dialog("New Connection", width="large")
def new_connection_modal() -> None:
    """Create a popup dialog for adding a new bank connection.

    Displays a form allowing the user to select a bank institution and create a new
    connection. When the user submits the form, it creates a new requisition link
    via the GoCardless API and stores it in the database.

    This function is decorated with @st.dialog to create a modal popup in the Streamlit UI.

    :raises: Exception if there's an error creating the connection or adding it to the database
    :returns: None
    """
    logger.info("Opening new connection modal")
    inst_mapping = get_institution_mapping()

    st.write("Please fill in your details:")
    institution = st.selectbox(
        "Bank", options=inst_mapping, help="Start typing or scroll to pick your bank"
    )
    if st.button("Create Connection"):
        logger.info(f"User initiated connection creation for institution: {institution}")
        callback = "http://localhost:8501/connections?gc_callback=1"
        try:
            logger.info(f"Creating link for institution ID: {inst_mapping[institution]}")
            link_data = create_link(gocardless_creds, callback, inst_mapping[institution])
            add_requisition_link(session, link_data)

            with st.spinner("Creating Connection..."):
                time.sleep(1)

            st.success("Connection Created Successfully.")
            logger.info(f"Connection created successfully for institution: {institution}")

            time.sleep(1)
            st.rerun()

        except Exception as e:
            logger.error(f"Failed to create connection for {institution}: {e!s}")
            st.error(f"Failed to create connection: {e!s}")
            raise


def render_row_button(link: RequisitionLink) -> None:
    """Render a requisition link as a clickable button in the UI.

    Creates a button for a single requisition link with a formatted label showing:
    [ID] | [Institution] | [colour-dot] [✔️/❌] [STATUS_NAME]

    When clicked, the button opens a details dialog for the requisition link.

    :param link: The requisition link to render
    :type link: RequisitionLink
    :returns: None
    """
    logger.debug(f"Rendering button for requisition link ID: {link.id}")
    code = link.status
    name = STATUS_NAMES.get(code, code)
    dot = STATUS_EMOJIS.get(code, "⬜")  # grey square fallback
    emoji = "✔️" if code == "LN" else "❌"

    label = f"{link.id} | {link.institution_id} | {dot} {emoji} {name}"
    if st.button(label, key=f"btn_{link.id}", use_container_width=True):
        logger.info(f"User clicked on requisition link ID: {link.id}")
        show_details(link)


@st.dialog("More Details")
def show_details(link: RequisitionLink) -> None:
    """Display detailed information about a requisition link in a modal dialog.

    Shows a modal dialog with detailed information about the requisition link,
    including ID, status, creation date, agreement, reference, authorization link,
    and SSN. Also provides buttons to authorize the bank connection (if applicable)
    and to delete the connection.

    This function is decorated with @st.dialog to create a modal popup in the Streamlit UI.

    :param link: The requisition link to display details for
    :type link: RequisitionLink
    :raises: Exception if there's an error deleting the requisition link
    :returns: None
    """
    logger.info(f"Showing details for requisition link ID: {link.id}")
    st.write("---")
    st.write(f"**Link ID:** {link.id}")
    st.write(f"**Status:** {STATUS_NAMES[link.status]}")
    st.write(f"**Created:** {link.created}")
    st.write(f"**Agreement:** {link.agreement}")
    st.write(f"**Reference:** {link.reference}")
    st.write("---")

    _, middle, _ = st.columns([1, 6, 1])
    with middle:
        # use a horizontal layout inside the middle column
        btn1, btn2 = st.columns([2, 1])
        is_enabled = link.status in ("CR", "EX")
        if is_enabled:
            logger.info(f"Authorization button enabled for link ID: {link.id}")
        else:
            logger.info(
                f"Authorization button disabled for link ID: {link.id} (status: {link.status})"
            )

        btn1.link_button(
            "Authorise bank connection",
            link.link,
            type="primary",
            use_container_width=False,
            disabled=not is_enabled,
        )

        if btn2.button("Delete", key=f"del_{link.id}"):
            logger.warning(f"User requested deletion of requisition link ID: {link.id}")
            try:
                delete_requisition_data_by_id(gocardless_creds, link.id)
                session.delete(link)
                session.commit()

                logger.info(f"Successfully deleted requisition link ID: {link.id}")
                with st.spinner("Deleting..."):
                    time.sleep(1)

                st.success("Connection Deleted")
                time.sleep(1)
                st.rerun()

            except Exception as e:
                logger.error(f"Failed to delete requisition link ID {link.id}: {e!s}")
                st.error(f"Failed to delete connection: {e!s}")
                raise


def clear_and_rerun() -> None:
    """Clear URL parameters and trigger a rerun of the Streamlit app.

    Uses Streamlit's experimental APIs to reset query parameters and then reruns
    the script to clear state.

    :returns: None
    """
    logger.info("Clearing URL parameters and triggering page rerun")
    st.query_params.clear()
    st.rerun()


def process_callback(params: QueryParamsProxy) -> None:
    """Process a callback from GoCardless after bank authorization.

    Handles the callback from GoCardless after a user has authorized a bank connection.
    Retrieves the updated requisition data from the GoCardless API, updates the
    requisition link status in the database, and displays a success message to the user.

    :param params: Query parameters from the callback URL
    :returns None
    :raises requests.RequestException: If there's an error communicating with the GoCardless API
    :raises Exception: If there's an error processing the callback or updating the database
    """
    logger.info(f"Processing GoCardless callback with params: {params}")
    req_id = params.get("ref")
    if not req_id:
        logger.warning("Missing requisition reference in callback parameters")
        st.error("Missing requisition reference in callback parameters.")
        return

    try:
        logger.info(f"Starting callback processing for requisition ID: {req_id}")

        # 1) Fetch requisition JSON
        requisition = fetch_requisition_data_by_id(gocardless_creds, req_id)
        new_status = requisition["status"]
        logger.info(f"Requisition status: {new_status}")

        # 2) Upsert requisition status
        upsert_requisition_status(session, req_id, new_status)

        # 3) Fetch and upsert each account's details
        account_ids = requisition.get("accounts", [])
        logger.info(f"Found {len(account_ids)} accounts linked to requisition")
        detailed_accounts = []
        for acct_id in account_ids:
            info = fetch_account_data_by_id(gocardless_creds, acct_id)
            detailed_accounts.append(info)
        upsert_bank_accounts(session, req_id, detailed_accounts)

        # 4) UI feedback
        logger.info("Displaying success message to user")
        with st.spinner("Connecting bank account and syncing data..."):
            time.sleep(2)
        st.success("Bank account connected and data synced!")

        # 5) Clear params & rerun
        logger.info("Callback processing completed successfully, clearing parameters")
        time.sleep(1)
        clear_and_rerun()

    except requests.RequestException as e:
        logger.error(f"API error during callback processing: {e!s}")
        st.error(f"API error: {e}")
        raise

    except Exception as e:
        logger.error(f"Unexpected error during callback processing: {e!s}")
        st.error(f"Unexpected error: {e}")
        raise


def render_table() -> None:
    """Render the table of requisition links in the UI.

    Fetches all requisition links from the database and renders them as a list
    of buttons in the UI. If no links are found, displays an error message.

    This function is the main display component for the connections page.

    :raises: Exception if there's an error fetching requisition links from the database
    :returns: None
    """
    logger.info("Rendering requisition links table")
    links = fetch_requisition_links(session)
    if not links:
        logger.info("No requisition links found in database")
        st.error("No connections, press 'Add Connection' to add a new connection.")
    else:
        logger.info(f"Rendering {len(links)} requisition links")
        for link in links:
            render_row_button(link)


# catch GoCardless Callback
# example: http://localhost:8501/connections?ref=1b3c1181-5eae-4219-881a-b3af1c1acdc1&gc_callback=1
# chase: http://localhost:8501/connections?ref=cb84aa32-3271-4909-a546-213babd4a8ec&gc_callback=1
params = st.query_params
logger.info(f"Page Params - {params}")
if params.get("gc_callback") and params.get("ref"):
    process_callback(params)

# ─── Top bar with "+ Connection" on the right ─────────────────────────────────
logger.info("Initializing UI components")
st.markdown("# Your Connections")
if st.button("Add Connection"):
    logger.info("User clicked 'Add Connection' button")
    new_connection_modal()

logger.info("Starting to render connections table")
render_table()
logger.info("Page rendering completed")
