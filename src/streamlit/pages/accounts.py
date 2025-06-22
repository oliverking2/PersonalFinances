"""Accounts page for streamlit."""

import streamlit as st
from sqlalchemy.orm import Session
from streamlit.delta_generator import DeltaGenerator

from src.mysql.gocardless import BankAccount
from src.streamlit.utils import get_gocardless_session

# Page config
st.set_page_config(page_title="Accounts", layout="wide")
st.title("Your Bank Accounts")

# Connect to your database
session: Session = get_gocardless_session()

# Fetch all accounts
accounts = session.query(BankAccount).all()
if not accounts:
    st.info("No bank accounts found. Please connect one via the Connections page.")
    st.stop()


# Helper: render a single card
def render_card(col: DeltaGenerator, acc: BankAccount) -> None:
    """Render a single card."""
    # every card is a fixed-size square with centred text
    card_html = f"""
    <div style="
        border:1px solid #ddd;
        border-radius:8px;
        padding:16px;
        text-align:center;
        height:150px;
        display:flex;
        flex-direction:column;
        justify-content:center;
        box-shadow:2px 2px 5px rgba(0,0,0,0.1);
        margin:8px;
    ">
        <strong style="font-size:1.1em;">{acc.display_name or acc.name}</strong>
        <small style="color:#666;">{acc.iban or acc.bban or ""}</small>
    </div>
    """
    col.markdown(card_html, unsafe_allow_html=True)
    # invisible button overlay (so clicking the card selects it)
    if col.button(" ", key=f"select_{acc.id}", use_container_width=True):
        st.session_state.selected_account = acc.id


# Build grid: 3 cards per row
n_cols = 3
rows = [accounts[i : i + n_cols] for i in range(0, len(accounts), n_cols)]

for row in rows:
    cols = st.columns(n_cols)
    for col, acc in zip(cols, row):
        render_card(col, acc)

# React to selection
if st.session_state.get("selected_account"):
    sel_id = st.session_state.selected_account
    sel = session.get(BankAccount, sel_id)
    st.write("---")
    st.subheader(f"Details for {sel.display_name or sel.name}")
    st.write(f"**Account ID:** {sel.id}")
    st.write(f"**IBAN:** {sel.iban or '-'}")
    st.write(f"**BIC:** {sel.bic or '-'}")
    st.write(f"**Currency:** {sel.currency}")
    st.write(f"**Type:** {sel.cash_account_type}")
    st.write(f"**Status:** {sel.status}")
    st.write(f"**Product:** {sel.product}")
    st.write(f"**Owner:** {sel.owner_name}")
