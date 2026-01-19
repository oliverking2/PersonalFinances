"""Streamlit utils module."""

import logging

from sqlalchemy.orm import Session

import streamlit as st
from src.postgres.core import create_session
from src.providers.gocardless.api.core import GoCardlessCredentials
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


def get_streamlit_logger(name: str) -> logging.Logger:
    """Get the Streamlit logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    return logger
