"""Bank setup page."""

import streamlit as st

ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]
INSTITUTION_ID = st.secrets["BANK1_INSTITUTION_ID"]
REDIRECT_URI = "http://localhost:8501/"
#
# st.header("Connect Bank 1")
# if "req_id_1" not in st.session_state:
#     if st.button("Start Connection"):
#         payload = {
#             "redirect": REDIRECT_URI,
#             "institution_id": INSTITUTION_ID,
#             "reference": "user-123",
#             "user_language": "EN",
#         }
#         resp = requests.post(
#             "https://bankaccountdata.gocardless.com/api/v2/requisitions/",
#             headers={"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"},
#             json=payload,
#         )
#         data = resp.json()
#         st.session_state.req_id_1 = data["id"]
#         st.session_state.link_1 = data["link"]
#         st.experimental_rerun()
#
# if "link_1" in st.session_state:
#     st.link_button(
#         "🔗 Connect to Bank 1", st.session_state.link_1, use_container_width=True
#     )  # Opens bank-auth page :contentReference[oaicite:8]{index=8}
