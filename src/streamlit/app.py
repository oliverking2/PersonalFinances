"""Main Streamlit application entry point.

This module serves as the main entry point for the Personal Finance Manager
Streamlit web application. It sets up the basic page configuration and
provides navigation to other pages.
"""

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

st.set_page_config(page_title="Personal Finance Manager", layout="wide")
st.title("Welcome to Your Finance Dashboard")
st.sidebar.success("Select a page above")
