"""Accounts Setup Page."""

import streamlit as st
from sqlalchemy.orm import Session

from src.mysql.gocardless import BankAccount

# page config
st.set_page_config(page_title="Accounts", layout="wide")
conn = st.connection("mysql_local")

# ─── Load accounts from DB ─────────────────────────────────────────────────
session: Session = conn.session
accounts = session.query(BankAccount).all()


@st.dialog("New Account", width="large")
def new_account_modal() -> None:
    """Create a popup for adding a new account."""
    st.write("Please fill in your details:")
    # username = st.text_input("Username")
    # email = st.text_input("Email address")
    # password = st.text_input("Password", type="password")
    if st.button("Create Account"):
        # create_account(username, email, password)
        st.rerun()  # close the dialog


# ─── Top bar with "+ Account" on the right ─────────────────────────────────
left, right = st.columns([9, 1])
with right:
    if st.button("Add Account"):
        new_account_modal()

with left:
    st.markdown("## Your Connected Accounts")

# ─── Display accounts as interactive squares ───────────────────────────────
if not accounts:
    st.info("No accounts set up yet. Click 'Add Account' to add one.")

else:
    cols_per_row = 3
    for row_start in range(0, len(accounts), cols_per_row):
        cols = st.columns(cols_per_row, gap="large")
        for col, acct in zip(cols, accounts[row_start : row_start + cols_per_row]):
            with col:
                # make each square a button with custom styling
                if st.button(acct.name, key=acct.id, help=f"{acct.currency} • {acct.id}"):
                    st.session_state.selected_account = acct.id
                # additional info under the button
                st.caption(f"Balance: {acct.metadata.get('balance', '-')}")
