-- Source model for recurring patterns table
-- Provides a clean interface to the recurring patterns data from PostgreSQL

SELECT
    ID,
    USER_ID,
    ACCOUNT_ID,
    TAG_ID,
    NAME,
    NOTES,
    EXPECTED_AMOUNT,
    CURRENCY,
    FREQUENCY,
    DIRECTION,
    ANCHOR_DATE,
    CAST(NEXT_EXPECTED_DATE AS TIMESTAMP) AS NEXT_EXPECTED_DATE,
    CAST(LAST_MATCHED_DATE AS TIMESTAMP)  AS LAST_MATCHED_DATE,
    CAST(END_DATE AS TIMESTAMP)           AS END_DATE,
    STATUS,
    SOURCE,
    MERCHANT_CONTAINS,
    AMOUNT_TOLERANCE_PCT,
    ADVANCED_RULES,
    MATCH_COUNT,
    CONFIDENCE_SCORE,
    OCCURRENCE_COUNT,
    DETECTION_REASON,
    AI_METADATA,
    CREATED_AT,
    UPDATED_AT
FROM {{ source('unified', 'recurring_patterns') }}
