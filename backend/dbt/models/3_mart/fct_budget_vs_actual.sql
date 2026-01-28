-- Budget vs Actual spending comparison
-- Compares monthly budgets against actual spending by tag for the current month
-- Used for budget tracking dashboards and alerts

WITH BUDGETS AS (
    SELECT
        ID     AS BUDGET_ID,
        USER_ID,
        TAG_ID,
        AMOUNT AS BUDGET_AMOUNT,
        CURRENCY,
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

-- Get spending for the current month by tag
-- Uses transaction splits for accurate tag-based spending
CURRENT_MONTH_SPENDING AS (
    SELECT
        SPL.TAG_ID,
        TXN.CURRENCY,
        SUM(SPL.AMOUNT)        AS SPENT_AMOUNT,
        COUNT(DISTINCT TXN.ID) AS TRANSACTION_COUNT
    FROM {{ ref('src_unified_transaction_splits') }} AS SPL
    INNER JOIN {{ ref('src_unified_transactions') }} AS TXN
        ON SPL.TRANSACTION_ID = TXN.ID
    WHERE
        TXN.AMOUNT < 0  -- Only spending transactions
        AND TXN.BOOKING_DATE >= DATE_TRUNC('month', CURRENT_DATE)
        AND TXN.BOOKING_DATE < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'
    GROUP BY
        SPL.TAG_ID,
        TXN.CURRENCY
),

-- Join budgets with spending
BUDGET_SPENDING AS (
    SELECT
        BUD.BUDGET_ID,
        BUD.USER_ID,
        BUD.TAG_ID,
        TAG.TAG_NAME,
        TAG.TAG_COLOUR,
        BUD.BUDGET_AMOUNT,
        BUD.CURRENCY,
        BUD.WARNING_THRESHOLD,
        COALESCE(SPD.SPENT_AMOUNT, 0)                     AS SPENT_AMOUNT,
        COALESCE(SPD.TRANSACTION_COUNT, 0)                AS TRANSACTION_COUNT,
        BUD.BUDGET_AMOUNT - COALESCE(SPD.SPENT_AMOUNT, 0) AS REMAINING_AMOUNT
    FROM BUDGETS AS BUD
    INNER JOIN TAGS AS TAG ON BUD.TAG_ID = TAG.TAG_ID
    LEFT JOIN CURRENT_MONTH_SPENDING AS SPD
        ON BUD.TAG_ID = SPD.TAG_ID AND BUD.CURRENCY = SPD.CURRENCY
)

SELECT
    BUDGET_ID,
    USER_ID,
    TAG_ID,
    TAG_NAME,
    TAG_COLOUR,
    BUDGET_AMOUNT,
    CURRENCY,
    WARNING_THRESHOLD,
    SPENT_AMOUNT,
    TRANSACTION_COUNT,
    REMAINING_AMOUNT,
    -- Calculate percentage used
    CASE
        WHEN BUDGET_AMOUNT > 0
            THEN ROUND(SPENT_AMOUNT / BUDGET_AMOUNT * 100, 2)
        ELSE 0
    END                                                                       AS PERCENTAGE_USED,
    -- Determine budget status
    CASE
        WHEN SPENT_AMOUNT >= BUDGET_AMOUNT THEN 'exceeded'
        WHEN BUDGET_AMOUNT > 0 AND SPENT_AMOUNT / BUDGET_AMOUNT >= WARNING_THRESHOLD THEN 'warning'
        ELSE 'ok'
    END                                                                       AS BUDGET_STATUS,
    -- Period info
    DATE_TRUNC('month', CURRENT_DATE)                                         AS PERIOD_START,
    DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day' AS PERIOD_END,
    STRFTIME(CURRENT_DATE, '%Y-%m')                                           AS PERIOD_KEY
FROM BUDGET_SPENDING
