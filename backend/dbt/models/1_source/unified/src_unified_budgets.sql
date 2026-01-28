-- Source model for unified budgets table
-- Provides a clean interface to the budgets data from PostgreSQL

SELECT
    ID,
    USER_ID,
    TAG_ID,
    AMOUNT,
    CURRENCY,
    PERIOD,
    WARNING_THRESHOLD,
    ENABLED,
    CREATED_AT,
    UPDATED_AT
FROM {{ source('unified', 'budgets') }}
