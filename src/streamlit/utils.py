"""Streamlit utils module."""

import streamlit as st
from sqlalchemy.orm import Session

from src.gocardless.api.core import GoCardlessCredentials
from src.postgres.utils import create_session
from src.utils.definitions import gocardless_database_url


# Cache the Session factory and return a scoped session
@st.cache_resource
def get_gocardless_session() -> Session:
    """Return a SQLAlchemy Session bound to the cached Engine."""
    return create_session(gocardless_database_url())


def get_gocardless_creds() -> GoCardlessCredentials:
    """Get or create some GoCardless Credentials."""
    if "gocardless_creds" not in st.session_state:
        st.session_state.gocardless_creds = GoCardlessCredentials()
    return st.session_state.gocardless_creds
