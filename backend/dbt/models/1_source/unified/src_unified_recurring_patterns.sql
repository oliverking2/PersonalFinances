-- Source model for recurring patterns table
-- Provides a clean interface to the recurring patterns data from PostgreSQL

SELECT
    ID,
    USER_ID,
    MERCHANT_PATTERN,
    ACCOUNT_ID,
    EXPECTED_AMOUNT,
    AMOUNT_VARIANCE,
    CURRENCY,
    FREQUENCY,
    ANCHOR_DATE,
    NEXT_EXPECTED_DATE,
    LAST_OCCURRENCE_DATE,
    CONFIDENCE_SCORE,
    OCCURRENCE_COUNT,
    STATUS,
    DISPLAY_NAME,
    NOTES,
    CREATED_AT,
    UPDATED_AT
FROM {{ source('unified', 'recurring_patterns') }}
