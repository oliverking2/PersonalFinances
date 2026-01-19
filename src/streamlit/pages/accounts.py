"""Accounts page for streamlit."""

import streamlit as st
from src.postgres.gocardless.models import BankAccount
from src.postgres.gocardless.operations.bank_accounts import get_active_accounts
from src.streamlit.utils import get_gocardless_session, get_streamlit_logger

logger = get_streamlit_logger("accounts_page")

session = get_gocardless_session()


ACCOUNT_STATUS_MAPPING = {
    "EXPIRED": "Expired",
    "READY": "Ready",
}

STATUS_EMOJIS = {
    "READY": "🟢",
    "EXPIRED": "🔴",
}


def render_row_button(account: BankAccount) -> None:
    """Render a button for each bank account in the table."""
    # \u00A0|\u00A0 adds a bit more space between the different elements
    friendly_name = account.requisition.friendly_name if account.requisition else "Unknown"
    status = account.status or "UNKNOWN"
    label = (
        f"{friendly_name} "
        f"\u00a0|\u00a0 {account.name} "
        f"\u00a0|\u00a0 {STATUS_EMOJIS.get(status, '⬜')} {ACCOUNT_STATUS_MAPPING.get(status, status)} "
    )

    if st.button(label, key=f"btn_{account.id}", use_container_width=True):
        logger.info(f"User clicked on account ID: {account.id}")
        show_details(account)


@st.dialog("More Details")
def show_details(account: BankAccount) -> None:
    """Display detailed information about a bank account in a modal dialog."""
    status = account.status or "UNKNOWN"
    st.write("---")
    st.write(f"**Account ID:** {account.id}")
    st.write(f"**Status:** {ACCOUNT_STATUS_MAPPING.get(status, status)}")
    st.write(f"**Name:** {account.name}")
    st.write(f"**Last Extract Date:** {account.dg_transaction_extract_date}")
    st.write("---")


def render_table() -> None:
    """Render the table of bank accounts."""
    accounts = get_active_accounts(session)
    if accounts:
        for account in accounts:
            logger.info(f"Rendering row for account ID: {account.id}")
            render_row_button(account)


# Page config
st.set_page_config(page_title="Accounts", layout="wide")
st.title("Your Bank Accounts")

logger.info("Starting to render connections table")
render_table()
logger.info("Page rendering completed")
