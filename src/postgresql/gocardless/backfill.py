"""Backfill the GoCardless Data."""

from src.gocardless.api.account import fetch_account_data_by_id
from src.gocardless.api.auth import GoCardlessCredentials
from src.gocardless.api.requisition import fetch_all_requisition_data
from src.postgresql.gocardless.models import RequisitionLink
from src.postgresql.gocardless.operations.bank_accounts import upsert_bank_accounts
from src.postgresql.gocardless.operations.requisitions import add_requisition_link
from src.streamlit.utils import get_gocardless_session


if __name__ == "__main__":
    creds = GoCardlessCredentials()
    session = get_gocardless_session()

    requisitions = fetch_all_requisition_data(creds)

    for requisition in requisitions:
        requisition_id = requisition["id"]
        link = session.get(RequisitionLink, requisition_id)
        if link is None:
            add_requisition_link(session, requisition)

        detailed_accounts = []
        for acct_id in requisition["accounts"]:
            info = fetch_account_data_by_id(creds, acct_id)
            detailed_accounts.append(info)
        upsert_bank_accounts(session, requisition_id, detailed_accounts)
