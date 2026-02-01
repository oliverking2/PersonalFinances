-- Budget vs Actual spending comparison
-- Compares budgets against actual spending by tag for the current period
-- Supports weekly, monthly, quarterly, and annual budget periods
-- Used for budget tracking dashboards and alerts

WITH BUDGETS AS (
    SELECT
        ID     AS BUDGET_ID,
        USER_ID,
        TAG_ID,
        AMOUNT AS BUDGET_AMOUNT,
        CURRENCY,
        PERIOD,
        WARNING_THRESHOLD,
        ENABLED
    FROM {{ ref('src_unified_budgets') }}
    WHERE ENABLED = TRUE
),

TAGS AS (
    SELECT
        ID     AS TAG_ID,
        NAME   AS TAG_NAME,
        COLOUR AS TAG_COLOUR
    FROM {{ ref('src_unified_tags') }}
),

-- Calculate period boundaries based on budget period type
BUDGET_PERIODS AS (
    SELECT
        BUDGET_ID,
        USER_ID,
        TAG_ID,
        BUDGET_AMOUNT,
        CURRENCY,
        PERIOD,
        WARNING_THRESHOLD,
        -- Period start calculation
        CASE PERIOD
            WHEN 'weekly' THEN DATE_TRUNC('week', CURRENT_DATE)
            WHEN 'monthly' THEN DATE_TRUNC('month', CURRENT_DATE)
            WHEN 'quarterly' THEN DATE_TRUNC('quarter', CURRENT_DATE)
            WHEN 'annual' THEN DATE_TRUNC('year', CURRENT_DATE)
            ELSE DATE_TRUNC('month', CURRENT_DATE)
        END AS PERIOD_START,
        -- Period end calculation
        CASE PERIOD
            WHEN 'weekly' THEN DATE_TRUNC('week', CURRENT_DATE) + INTERVAL '7 days' - INTERVAL '1 day'
            WHEN 'monthly' THEN DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day'
            WHEN 'quarterly' THEN DATE_TRUNC('quarter', CURRENT_DATE) + INTERVAL '3 months' - INTERVAL '1 day'
            WHEN 'annual' THEN DATE_TRUNC('year', CURRENT_DATE) + INTERVAL '1 year' - INTERVAL '1 day'
            ELSE DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day'
        END AS PERIOD_END,
        -- Period key for display
        CASE PERIOD
            WHEN 'weekly' THEN STRFTIME(CURRENT_DATE, '%G-W%V')
            WHEN 'monthly' THEN STRFTIME(CURRENT_DATE, '%Y-%m')
            WHEN 'quarterly' THEN CONCAT(STRFTIME(CURRENT_DATE, '%Y'), '-Q', CAST(QUARTER(CURRENT_DATE) AS VARCHAR))
            WHEN 'annual' THEN STRFTIME(CURRENT_DATE, '%Y')
            ELSE STRFTIME(CURRENT_DATE, '%Y-%m')
        END AS PERIOD_KEY
    FROM BUDGETS
),

-- Get spending for each budget based on its period
CURRENT_PERIOD_SPENDING AS (
    SELECT
        BUDGET_PERIODS.BUDGET_ID,
        SUM(SPLITS.AMOUNT)     AS SPENT_AMOUNT,
        COUNT(DISTINCT TXN.ID) AS TRANSACTION_COUNT
    FROM BUDGET_PERIODS
    INNER JOIN {{ ref('src_unified_transaction_splits') }} AS SPLITS
        ON BUDGET_PERIODS.TAG_ID = SPLITS.TAG_ID
    INNER JOIN {{ ref('src_unified_transactions') }} AS TXN
        ON SPLITS.TRANSACTION_ID = TXN.ID
    WHERE
        TXN.AMOUNT < 0  -- Only spending transactions
        AND TXN.BOOKING_DATE >= BUDGET_PERIODS.PERIOD_START
        AND TXN.BOOKING_DATE <= BUDGET_PERIODS.PERIOD_END
        AND TXN.CURRENCY = BUDGET_PERIODS.CURRENCY
    GROUP BY BUDGET_PERIODS.BUDGET_ID
),

-- Join budgets with spending
BUDGET_SPENDING AS (
    SELECT
        BUDGET_PERIODS.BUDGET_ID,
        BUDGET_PERIODS.USER_ID,
        BUDGET_PERIODS.TAG_ID,
        TAGS.TAG_NAME,
        TAGS.TAG_COLOUR,
        BUDGET_PERIODS.BUDGET_AMOUNT,
        BUDGET_PERIODS.CURRENCY,
        BUDGET_PERIODS.PERIOD,
        BUDGET_PERIODS.WARNING_THRESHOLD,
        BUDGET_PERIODS.PERIOD_START,
        BUDGET_PERIODS.PERIOD_END,
        BUDGET_PERIODS.PERIOD_KEY,
        COALESCE(SPENDING.SPENT_AMOUNT, 0)                                AS SPENT_AMOUNT,
        COALESCE(SPENDING.TRANSACTION_COUNT, 0)                           AS TRANSACTION_COUNT,
        BUDGET_PERIODS.BUDGET_AMOUNT - COALESCE(SPENDING.SPENT_AMOUNT, 0) AS REMAINING_AMOUNT,
        -- Days remaining in period
        DATEDIFF('day', CURRENT_DATE, BUDGET_PERIODS.PERIOD_END)          AS DAYS_REMAINING
    FROM BUDGET_PERIODS
    INNER JOIN TAGS ON BUDGET_PERIODS.TAG_ID = TAGS.TAG_ID
    LEFT JOIN CURRENT_PERIOD_SPENDING AS SPENDING ON BUDGET_PERIODS.BUDGET_ID = SPENDING.BUDGET_ID
)

SELECT
    BUDGET_ID,
    USER_ID,
    TAG_ID,
    TAG_NAME,
    TAG_COLOUR,
    BUDGET_AMOUNT,
    CURRENCY,
    PERIOD,
    WARNING_THRESHOLD,
    SPENT_AMOUNT,
    TRANSACTION_COUNT,
    REMAINING_AMOUNT,
    DAYS_REMAINING,
    PERIOD_START,
    PERIOD_END,
    PERIOD_KEY,
    -- Calculate percentage used
    CASE
        WHEN BUDGET_AMOUNT > 0
            THEN ROUND(SPENT_AMOUNT / BUDGET_AMOUNT * 100, 2)
        ELSE 0
    END AS PERCENTAGE_USED,
    -- Determine budget status
    CASE
        WHEN SPENT_AMOUNT >= BUDGET_AMOUNT THEN 'exceeded'
        WHEN BUDGET_AMOUNT > 0 AND SPENT_AMOUNT / BUDGET_AMOUNT >= WARNING_THRESHOLD THEN 'warning'
        ELSE 'ok'
    END AS BUDGET_STATUS
FROM BUDGET_SPENDING
