-- Budget Forecast
-- Projects when budgets will be exceeded based on historical spending patterns
-- Uses last 90 days of spending to calculate daily average per tag
-- Calculates days until budget exhaustion and projected end-of-period spending

WITH BUDGET_STATUS AS (
    -- Get current budget status from fct_budget_vs_actual
    SELECT
        BUDGET_ID,
        USER_ID,
        TAG_ID,
        TAG_NAME,
        TAG_COLOUR,
        BUDGET_AMOUNT,
        CURRENCY,
        PERIOD,
        SPENT_AMOUNT,
        REMAINING_AMOUNT,
        PERCENTAGE_USED,
        BUDGET_STATUS,
        PERIOD_START,
        PERIOD_END,
        PERIOD_KEY,
        DAYS_REMAINING
    FROM {{ ref('fct_budget_vs_actual') }}
),

-- Calculate historical daily average spending per tag (last 90 days)
HISTORICAL_SPENDING AS (
    SELECT
        TAG_ID,
        CURRENCY,
        -- Average daily spending over the last 90 days
        SUM(TOTAL_SPENDING) / 90.0                     AS DAILY_AVG_SPENDING,
        -- Total spending over last 90 days
        SUM(TOTAL_SPENDING)                            AS TOTAL_90_DAY_SPENDING,
        -- Count of days with spending (for reference)
        COUNT(CASE WHEN TOTAL_SPENDING > 0 THEN 1 END) AS DAYS_WITH_SPENDING
    FROM {{ ref('fct_daily_spending_by_tag') }}
    WHERE
        TAG_ID IS NOT NULL
        AND SPENDING_DATE >= CURRENT_DATE - INTERVAL '90 days'
        AND SPENDING_DATE < CURRENT_DATE
    GROUP BY TAG_ID, CURRENCY
),

-- Join budgets with historical spending patterns
BUDGET_FORECAST AS (
    SELECT
        BUDGET_STATUS.BUDGET_ID,
        BUDGET_STATUS.USER_ID,
        BUDGET_STATUS.TAG_ID,
        BUDGET_STATUS.TAG_NAME,
        BUDGET_STATUS.TAG_COLOUR,
        BUDGET_STATUS.BUDGET_AMOUNT,
        BUDGET_STATUS.CURRENCY,
        BUDGET_STATUS.PERIOD,
        BUDGET_STATUS.SPENT_AMOUNT,
        BUDGET_STATUS.REMAINING_AMOUNT,
        BUDGET_STATUS.PERCENTAGE_USED,
        BUDGET_STATUS.BUDGET_STATUS,
        BUDGET_STATUS.PERIOD_START,
        BUDGET_STATUS.PERIOD_END,
        BUDGET_STATUS.PERIOD_KEY,
        BUDGET_STATUS.DAYS_REMAINING,
        -- Historical spending data
        COALESCE(HIST.DAILY_AVG_SPENDING, 0)
            AS DAILY_AVG_SPENDING,
        COALESCE(HIST.TOTAL_90_DAY_SPENDING, 0)
            AS TOTAL_90_DAY_SPENDING,
        COALESCE(HIST.DAYS_WITH_SPENDING, 0)
            AS DAYS_WITH_SPENDING_90D,
        -- Projected spending at end of period
        -- current_spent + (daily_avg * days_remaining)
        BUDGET_STATUS.SPENT_AMOUNT
        + (COALESCE(HIST.DAILY_AVG_SPENDING, 0) * BUDGET_STATUS.DAYS_REMAINING) AS PROJECTED_TOTAL,
        -- Days until budget is exhausted (if any spending)
        CASE
            WHEN COALESCE(HIST.DAILY_AVG_SPENDING, 0) > 0
                THEN BUDGET_STATUS.REMAINING_AMOUNT / HIST.DAILY_AVG_SPENDING  -- No spending history, can't project
        END
            AS DAYS_UNTIL_EXHAUSTED
    FROM BUDGET_STATUS
    LEFT JOIN HISTORICAL_SPENDING AS HIST
        ON BUDGET_STATUS.TAG_ID = HIST.TAG_ID AND BUDGET_STATUS.CURRENCY = HIST.CURRENCY
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
    SPENT_AMOUNT,
    REMAINING_AMOUNT,
    PERCENTAGE_USED,
    BUDGET_STATUS,
    PERIOD_START,
    PERIOD_END,
    PERIOD_KEY,
    DAYS_REMAINING,
    DAILY_AVG_SPENDING,
    TOTAL_90_DAY_SPENDING,
    DAYS_WITH_SPENDING_90D,
    PROJECTED_TOTAL,
    DAYS_UNTIL_EXHAUSTED,
    -- Projected exceed date (if budget will be exceeded)
    CASE
        WHEN DAYS_UNTIL_EXHAUSTED IS NOT NULL AND DAYS_UNTIL_EXHAUSTED >= 0
            THEN CURRENT_DATE + CAST(FLOOR(DAYS_UNTIL_EXHAUSTED) AS INTEGER)
    END AS PROJECTED_EXCEED_DATE,
    -- Will budget exceed before period ends?
    CASE
        WHEN BUDGET_STATUS = 'exceeded' THEN TRUE
        WHEN DAYS_UNTIL_EXHAUSTED IS NOT NULL AND DAYS_UNTIL_EXHAUSTED < DAYS_REMAINING THEN TRUE
        ELSE FALSE
    END AS WILL_EXCEED_IN_PERIOD,
    -- Projected percentage at end of period
    CASE
        WHEN BUDGET_AMOUNT > 0
            THEN ROUND(PROJECTED_TOTAL / BUDGET_AMOUNT * 100, 2)
        ELSE 0
    END AS PROJECTED_PERCENTAGE,
    -- Risk level for UI display
    CASE
        WHEN BUDGET_STATUS = 'exceeded' THEN 'critical'
        WHEN DAYS_UNTIL_EXHAUSTED IS NOT NULL AND DAYS_UNTIL_EXHAUSTED < DAYS_REMAINING THEN 'high'
        WHEN PROJECTED_TOTAL > BUDGET_AMOUNT * 0.9 THEN 'medium'
        ELSE 'low'
    END AS RISK_LEVEL
FROM BUDGET_FORECAST
ORDER BY
    -- Order by urgency: already exceeded, then by days until exhausted
    CASE WHEN BUDGET_STATUS = 'exceeded' THEN 0 ELSE 1 END,
    DAYS_UNTIL_EXHAUSTED NULLS LAST
