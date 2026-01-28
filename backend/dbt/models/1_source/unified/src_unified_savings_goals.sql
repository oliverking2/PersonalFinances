-- Source model for unified savings_goals table
-- Provides a clean interface to the savings goals data from PostgreSQL

SELECT
    ID,
    USER_ID,
    NAME,
    TARGET_AMOUNT,
    CURRENT_AMOUNT,
    CURRENCY,
    DEADLINE,
    ACCOUNT_ID,
    STATUS,
    NOTES,
    CREATED_AT,
    UPDATED_AT
FROM {{ source('unified', 'savings_goals') }}
