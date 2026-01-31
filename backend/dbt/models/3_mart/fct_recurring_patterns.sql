-- Fact table for recurring payment patterns
-- Reads from PostgreSQL recurring_patterns table (synced from detection)
-- Provides next expected dates and monthly equivalents for display

WITH PATTERNS AS (
    -- All patterns from PostgreSQL (detection syncs here, users manage status here)
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
    -- Exclude dismissed patterns from the mart
    WHERE PAT.STATUS NOT IN ('dismissed')
),

-- Calculate next expected dates if not set by user
WITH_NEXT_DATE AS (
    SELECT
        PAT.*,
        -- Use user-set date if available, otherwise calculate from frequency
        CASE
            WHEN PAT.USER_NEXT_DATE IS NOT NULL THEN PAT.USER_NEXT_DATE
            WHEN PAT.FREQUENCY = 'weekly'
                THEN
                    PAT.LAST_OCCURRENCE_DATE + INTERVAL '7 days'
            WHEN PAT.FREQUENCY = 'fortnightly'
                THEN
                    PAT.LAST_OCCURRENCE_DATE + INTERVAL '14 days'
            WHEN PAT.FREQUENCY = 'monthly'
                THEN
                    PAT.LAST_OCCURRENCE_DATE + INTERVAL '1 month'
            WHEN PAT.FREQUENCY = 'quarterly'
                THEN
                    PAT.LAST_OCCURRENCE_DATE + INTERVAL '3 months'
            WHEN PAT.FREQUENCY = 'annual'
                THEN
                    PAT.LAST_OCCURRENCE_DATE + INTERVAL '1 year'
        END AS NEXT_EXPECTED_DATE
    FROM PATTERNS AS PAT
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
    CAST(LAST_OCCURRENCE_DATE AS DATE)                                                   AS LAST_OCCURRENCE_DATE,
    CAST(NEXT_EXPECTED_DATE AS DATE)                                                     AS NEXT_EXPECTED_DATE,
    -- All patterns in this table are managed (synced from detection or user-created)
    TRUE                                                                                 AS IS_USER_MANAGED,
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
    END                                                                                  AS MONTHLY_EQUIVALENT,
    -- Is the pattern overdue? (past expected date + 7-day grace period)
    COALESCE(CAST(NEXT_EXPECTED_DATE AS DATE) < CURRENT_DATE - INTERVAL '7 days', FALSE) AS IS_OVERDUE,
    -- Days until next expected payment
    DATE_DIFF('day', CURRENT_DATE, CAST(NEXT_EXPECTED_DATE AS DATE))                     AS DAYS_UNTIL_NEXT
FROM WITH_NEXT_DATE
