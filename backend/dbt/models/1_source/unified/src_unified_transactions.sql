-- Source model for unified transactions table
-- Provides a clean interface to the transactions data from PostgreSQL
-- Excludes reconciled transactions (pending transactions replaced by booked versions)

SELECT
    ID,
    ACCOUNT_ID,
    PROVIDER_ID,
    BOOKING_DATE,
    VALUE_DATE,
    AMOUNT,
    CURRENCY,
    COUNTERPARTY_NAME,
    COUNTERPARTY_ACCOUNT,
    DESCRIPTION,
    CATEGORY,
    SYNCED_AT
FROM {{ source('unified', 'transactions') }}
WHERE STATUS = 'active'
