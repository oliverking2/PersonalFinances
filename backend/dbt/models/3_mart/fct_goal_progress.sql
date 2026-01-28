-- Goal progress fact table
-- Tracks savings goal progress with calculated metrics
-- For account-linked goals, can join with account balances for auto-tracking

WITH GOALS AS (
    SELECT
        ID   AS GOAL_ID,
        USER_ID,
        NAME AS GOAL_NAME,
        TARGET_AMOUNT,
        CURRENT_AMOUNT,
        CURRENCY,
        DEADLINE,
        ACCOUNT_ID,
        STATUS,
        NOTES,
        CREATED_AT,
        UPDATED_AT
    FROM {{ ref('src_unified_savings_goals') }}
),

ACCOUNTS AS (
    SELECT
        ACCOUNT_ID,
        DISPLAY_NAME   AS ACCOUNT_NAME,
        BALANCE_AMOUNT AS ACCOUNT_BALANCE,
        BALANCE_CURRENCY
    FROM {{ ref('dim_accounts') }}
),

-- Calculate effective current amount once
GOALS_WITH_BALANCE AS (
    SELECT
        GOL.*,
        ACC.ACCOUNT_NAME,
        ACC.ACCOUNT_BALANCE,
        -- For account-linked goals, use account balance; otherwise use manual current_amount
        COALESCE(ACC.ACCOUNT_BALANCE, GOL.CURRENT_AMOUNT) AS EFFECTIVE_AMOUNT
    FROM GOALS AS GOL
    LEFT JOIN ACCOUNTS AS ACC ON GOL.ACCOUNT_ID = ACC.ACCOUNT_ID
)

SELECT
    GOAL_ID,
    USER_ID,
    GOAL_NAME,
    TARGET_AMOUNT,
    EFFECTIVE_AMOUNT                 AS CURRENT_AMOUNT,
    CURRENCY,
    DEADLINE,
    ACCOUNT_ID,
    ACCOUNT_NAME,
    STATUS,
    NOTES,
    -- Calculate progress percentage
    CASE
        WHEN TARGET_AMOUNT > 0
            THEN ROUND(EFFECTIVE_AMOUNT / TARGET_AMOUNT * 100, 2)
        ELSE 0
    END                              AS PROGRESS_PERCENTAGE,
    -- Calculate remaining amount
    TARGET_AMOUNT - EFFECTIVE_AMOUNT AS REMAINING_AMOUNT,
    -- Days until deadline (null if no deadline)
    CASE
        WHEN DEADLINE IS NOT NULL
            THEN DATE_DIFF('day', CURRENT_DATE, DEADLINE::DATE)
    END                              AS DAYS_REMAINING,
    -- Is goal overdue?
    COALESCE(
        DEADLINE IS NOT NULL
        AND DEADLINE < CURRENT_TIMESTAMP
        AND STATUS = 'active',
        FALSE
    )                                AS IS_OVERDUE,
    -- Is goal on track? (simple linear projection)
    CASE
        WHEN
            DEADLINE IS NOT NULL
            AND STATUS = 'active'
            AND DATE_DIFF('day', CREATED_AT::DATE, CURRENT_DATE) > 0
            AND DATE_DIFF('day', CURRENT_DATE, DEADLINE::DATE) > 0
            THEN
                -- Calculate if current progress rate will reach target by deadline
                COALESCE(
                    (EFFECTIVE_AMOUNT / DATE_DIFF('day', CREATED_AT::DATE, CURRENT_DATE))
                    * DATE_DIFF('day', CREATED_AT::DATE, DEADLINE::DATE) >= TARGET_AMOUNT,
                    FALSE
                )
    END                              AS IS_ON_TRACK,
    CREATED_AT,
    UPDATED_AT
FROM GOALS_WITH_BALANCE
