-- depends_on: {{ source('dagster','gocardless_raw_transactions') }}
-- Loads transaction data from PostgreSQL gc_transactions table.

SELECT
    account_id,
    transaction_id,
    booking_date,
    value_date,
    booking_datetime,
    transaction_amount,
    currency,
    creditor_name,
    creditor_account,
    debtor_name,
    debtor_account,
    remittance_information,
    bank_transaction_code,
    proprietary_bank_code,
    status,
    internal_transaction_id,
    extracted_at
FROM pg.gc_transactions
WHERE account_id IS NOT NULL
