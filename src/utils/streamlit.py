"""Streamlit Util functions."""

import streamlit as st

from src.gocardless.api.auth import GoCardlessCredentials


def get_gocardless_creds() -> GoCardlessCredentials:
    """Get or create some GoCardless Credentials."""
    if "gocardless_creds" not in st.session_state:
        st.session_state.gocardless_creds = GoCardlessCredentials()
    return st.session_state.gocardless_creds
