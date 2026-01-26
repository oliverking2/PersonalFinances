-- Source model for unified transaction_splits table
-- Provides a clean interface to the split allocations from PostgreSQL

SELECT
    ID,
    TRANSACTION_ID,
    TAG_ID,
    AMOUNT,
    CREATED_AT
FROM {{ source('unified', 'transaction_splits') }}
