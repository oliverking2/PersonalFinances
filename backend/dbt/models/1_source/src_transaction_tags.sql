-- Source model for unified transaction_tags junction table
-- Provides a clean interface to the transaction-tag relationships from PostgreSQL

SELECT
    TRANSACTION_ID,
    TAG_ID,
    CREATED_AT
FROM {{ source('unified', 'transaction_tags') }}
