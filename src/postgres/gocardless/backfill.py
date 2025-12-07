"""Backfill the GoCardless Data."""

from src.gocardless.api.account import get_account_data_by_id
from src.gocardless.api.agreements import get_all_agreements
from src.gocardless.api.core import GoCardlessCredentials
from src.gocardless.api.requisition import get_all_requisition_data
from src.postgres.gocardless.models import RequisitionLink
from src.postgres.gocardless.operations.agreements import upsert_agreement
from src.postgres.gocardless.operations.bank_accounts import upsert_bank_accounts
from src.postgres.gocardless.operations.requisitions import add_requisition_link
from src.postgres.utils import create_session
from src.utils.definitions import gocardless_database_url


if __name__ == "__main__":
    creds = GoCardlessCredentials()
    session = create_session(gocardless_database_url())

    requisitions = get_all_requisition_data(creds)

    for requisition in requisitions:
        requisition_id = requisition["id"]
        link = session.get(RequisitionLink, requisition_id)
        if link is None:
            add_requisition_link(session, requisition)

        detailed_accounts = []
        for acct_id in requisition["accounts"]:
            info = get_account_data_by_id(creds, acct_id)
            detailed_accounts.append(info)
        upsert_bank_accounts(session, requisition_id, detailed_accounts)

    agreements = get_all_agreements(creds)
    for agreement in agreements:
        upsert_agreement(session, agreement)
