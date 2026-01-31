-- Source model for balance snapshots table
-- Provides historical balance data captured at each sync for trend analysis

SELECT
    ID,
    ACCOUNT_ID,
    BALANCE_AMOUNT,
    BALANCE_CURRENCY,
    BALANCE_TYPE,
    TOTAL_VALUE,
    UNREALISED_PNL,
    SOURCE_UPDATED_AT,
    CAPTURED_AT
FROM {{ source('unified', 'balance_snapshots') }}
