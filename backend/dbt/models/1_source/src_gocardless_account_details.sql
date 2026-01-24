-- depends_on: {{ source('dagster','gocardless_raw_account_details') }}
-- Loads account details from PostgreSQL gc_bank_accounts table.

SELECT
    id AS account_id,
    bban,
    bic,
    cash_account_type,
    currency,
    details,
    display_name,
    iban,
    linked_accounts,
    msisdn,
    name,
    owner_address_unstructured,
    owner_name,
    product,
    status,
    scan,
    usage,
    requisition_id,
    dg_transaction_extract_date
FROM pg.gc_bank_accounts
WHERE id IS NOT NULL
