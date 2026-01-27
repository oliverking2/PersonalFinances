-- Source model for unified accounts table
-- Provides a clean interface to the accounts data from PostgreSQL

SELECT
    ID,
    CONNECTION_ID,
    PROVIDER_ID,
    ACCOUNT_TYPE,
    CATEGORY,
    CREDIT_LIMIT,
    DISPLAY_NAME,
    NAME,
    IBAN,
    CURRENCY,
    STATUS,
    LAST_SYNCED_AT,
    SYNCED_AT,
    BALANCE_AMOUNT,
    BALANCE_CURRENCY,
    BALANCE_TYPE,
    BALANCE_UPDATED_AT,
    TOTAL_VALUE,
    UNREALISED_PNL
FROM {{ source('unified', 'accounts') }}
