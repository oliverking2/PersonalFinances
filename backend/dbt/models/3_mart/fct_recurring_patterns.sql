-- Fact table for recurring payment patterns
-- Merges detected patterns with user-managed patterns from the database
-- Provides next expected dates and monthly equivalents for display

WITH DETECTED AS (
    -- Auto-detected patterns from transaction analysis
    SELECT
        ACCOUNT_ID,
        USER_ID,
        MERCHANT_KEY,
        MERCHANT_NAME,
        DIRECTION,
        CURRENCY,
        OCCURRENCE_COUNT,
        -- Use latest transaction amount (reflects current price after any changes)
        LATEST_AMOUNT      AS EXPECTED_AMOUNT,
        AMOUNT_VARIANCE_PCT,
        DETECTED_FREQUENCY AS FREQUENCY,
        CONFIDENCE_SCORE,
        LAST_OCCURRENCE,
        FIRST_OCCURRENCE
    FROM {{ ref('int_recurring_candidates') }}
    WHERE
        CONFIDENCE_SCORE >= 0.2  -- Very low threshold to catch patterns with limited data
        AND DETECTED_FREQUENCY != 'irregular'  -- Still exclude truly irregular patterns
),

USER_PATTERNS AS (
    -- User-managed patterns from the database
    SELECT
        PAT.ID                 AS PATTERN_ID,
        PAT.USER_ID,
        PAT.ACCOUNT_ID,
        PAT.MERCHANT_PATTERN,
        PAT.EXPECTED_AMOUNT,
        PAT.AMOUNT_VARIANCE,
        PAT.CURRENCY,
        PAT.FREQUENCY,
        PAT.DIRECTION,
        PAT.STATUS,
        PAT.CONFIDENCE_SCORE,
        PAT.OCCURRENCE_COUNT,
        PAT.DISPLAY_NAME,
        PAT.NOTES,
        PAT.LAST_OCCURRENCE_DATE,
        PAT.NEXT_EXPECTED_DATE AS USER_NEXT_DATE,
        PAT.CREATED_AT,
        PAT.UPDATED_AT
    FROM {{ ref('src_unified_recurring_patterns') }} AS PAT
),

-- Merge detected and user patterns (user patterns take precedence)
MERGED AS (
    SELECT
        COALESCE(USR.PATTERN_ID, GEN_RANDOM_UUID())             AS PATTERN_ID,
        COALESCE(USR.USER_ID, DET.USER_ID)                      AS USER_ID,
        COALESCE(USR.ACCOUNT_ID, DET.ACCOUNT_ID)                AS ACCOUNT_ID,
        COALESCE(USR.MERCHANT_PATTERN, DET.MERCHANT_KEY)        AS MERCHANT_PATTERN,
        COALESCE(USR.EXPECTED_AMOUNT, DET.EXPECTED_AMOUNT)      AS EXPECTED_AMOUNT,
        COALESCE(USR.AMOUNT_VARIANCE, DET.AMOUNT_VARIANCE_PCT)  AS AMOUNT_VARIANCE,
        COALESCE(USR.CURRENCY, DET.CURRENCY, 'GBP')             AS CURRENCY,
        COALESCE(USR.FREQUENCY, DET.FREQUENCY)                  AS FREQUENCY,
        COALESCE(USR.DIRECTION, DET.DIRECTION, 'expense')       AS DIRECTION,
        COALESCE(USR.STATUS, 'detected')                        AS STATUS,
        COALESCE(USR.CONFIDENCE_SCORE, DET.CONFIDENCE_SCORE)    AS CONFIDENCE_SCORE,
        COALESCE(USR.OCCURRENCE_COUNT, DET.OCCURRENCE_COUNT)    AS OCCURRENCE_COUNT,
        COALESCE(USR.DISPLAY_NAME, DET.MERCHANT_NAME)           AS DISPLAY_NAME,
        USR.NOTES,
        COALESCE(USR.LAST_OCCURRENCE_DATE, DET.LAST_OCCURRENCE) AS LAST_OCCURRENCE_DATE,
        USR.USER_NEXT_DATE,
        DET.LAST_OCCURRENCE                                     AS DETECTED_LAST_OCCURRENCE,
        USR.CREATED_AT,
        USR.UPDATED_AT,
        -- Flag whether this is from user patterns or detection
        COALESCE(USR.PATTERN_ID IS NOT NULL, FALSE)             AS IS_USER_MANAGED
    FROM DETECTED AS DET
    FULL OUTER JOIN USER_PATTERNS AS USR
        ON
            DET.ACCOUNT_ID = USR.ACCOUNT_ID
            AND DET.MERCHANT_KEY = USR.MERCHANT_PATTERN
    WHERE COALESCE(USR.STATUS, 'detected') NOT IN ('dismissed')
),

-- Calculate next expected dates
WITH_NEXT_DATE AS (
    SELECT
        MRG.*,
        -- Calculate next expected date based on frequency
        CASE
            WHEN MRG.USER_NEXT_DATE IS NOT NULL THEN MRG.USER_NEXT_DATE
            WHEN MRG.FREQUENCY = 'weekly'
                THEN
                    MRG.LAST_OCCURRENCE_DATE + INTERVAL '7 days'
            WHEN MRG.FREQUENCY = 'fortnightly'
                THEN
                    MRG.LAST_OCCURRENCE_DATE + INTERVAL '14 days'
            WHEN MRG.FREQUENCY = 'monthly'
                THEN
                    MRG.LAST_OCCURRENCE_DATE + INTERVAL '1 month'
            WHEN MRG.FREQUENCY = 'quarterly'
                THEN
                    MRG.LAST_OCCURRENCE_DATE + INTERVAL '3 months'
            WHEN MRG.FREQUENCY = 'annual'
                THEN
                    MRG.LAST_OCCURRENCE_DATE + INTERVAL '1 year'
        END AS NEXT_EXPECTED_DATE
    FROM MERGED AS MRG
)

SELECT
    PATTERN_ID,
    USER_ID,
    ACCOUNT_ID,
    MERCHANT_PATTERN,
    DISPLAY_NAME,
    EXPECTED_AMOUNT,
    AMOUNT_VARIANCE,
    CURRENCY,
    FREQUENCY,
    DIRECTION,
    STATUS,
    CONFIDENCE_SCORE,
    OCCURRENCE_COUNT,
    NOTES,
    LAST_OCCURRENCE_DATE,
    NEXT_EXPECTED_DATE,
    IS_USER_MANAGED,
    CREATED_AT,
    UPDATED_AT,
    -- Calculate monthly equivalent amount for comparison
    -- For income, keep positive; for expense, keep positive for display
    CASE FREQUENCY
        WHEN 'weekly' THEN ABS(EXPECTED_AMOUNT) * 4.33
        WHEN 'fortnightly' THEN ABS(EXPECTED_AMOUNT) * 2.17
        WHEN 'monthly' THEN ABS(EXPECTED_AMOUNT)
        WHEN 'quarterly' THEN ABS(EXPECTED_AMOUNT) / 3
        WHEN 'annual' THEN ABS(EXPECTED_AMOUNT) / 12
        ELSE ABS(EXPECTED_AMOUNT)
    END                                                                    AS MONTHLY_EQUIVALENT,
    -- Is the pattern overdue? (past expected date + 7-day grace period)
    COALESCE(NEXT_EXPECTED_DATE < CURRENT_DATE - INTERVAL '7 days', FALSE) AS IS_OVERDUE,
    -- Days until next expected payment
    DATE_DIFF('day', CURRENT_DATE, NEXT_EXPECTED_DATE)                     AS DAYS_UNTIL_NEXT
FROM WITH_NEXT_DATE
