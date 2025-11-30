"""Streamlit utils module."""

import streamlit as st
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session

from src.gocardless.api.auth import GoCardlessCredentials
from src.utils.definitions import gocardless_database_url


@st.cache_resource
def get_gocardless_engine() -> Engine:
    """Create and cache a SQLAlchemy Engine using env vars.

    MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE.
    """
    return create_engine(gocardless_database_url())


# Cache the Session factory and return a scoped session
@st.cache_resource
def get_gocardless_session() -> Session:
    """Return a SQLAlchemy Session bound to the cached Engine."""
    engine = get_gocardless_engine()
    session_local = sessionmaker(bind=engine)
    return session_local()  # sessions are lightweight and thread-safe


def get_gocardless_creds() -> GoCardlessCredentials:
    """Get or create some GoCardless Credentials."""
    if "gocardless_creds" not in st.session_state:
        st.session_state.gocardless_creds = GoCardlessCredentials()
    return st.session_state.gocardless_creds
