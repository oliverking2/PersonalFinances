-- Spending pace comparison: current month spending vs 90-day historical daily average
-- Shows whether user is spending faster or slower than their recent average
-- Uses FULL OUTER JOIN so rows appear even with no current-month transactions or no history

WITH CURRENT_MONTH_SPENDING AS (
    -- Get current month's total spending from monthly trends
    SELECT
        USER_ID,
        CURRENCY,
        TOTAL_SPENDING AS MONTH_SPENDING_SO_FAR
    FROM {{ ref('fct_monthly_trends') }}
    WHERE
        MONTH_START = DATE_TRUNC('month', CURRENT_DATE)::DATE
),

HISTORICAL_DAILY AS (
    -- Calculate average daily spending from the last 90 days
    -- Sum across all tags to get total daily spending per user
    SELECT
        USER_ID,
        CURRENCY,
        SUM(TOTAL_SPENDING) / 90.0 AS AVG_DAILY_SPENDING
    FROM {{ ref('fct_daily_spending_by_tag') }}
    WHERE
        SPENDING_DATE >= CURRENT_DATE - INTERVAL '90 days'
        AND SPENDING_DATE < DATE_TRUNC('month', CURRENT_DATE)::DATE
    GROUP BY USER_ID, CURRENCY
),

-- Pre-compute month metadata to avoid INTERVAL->INTEGER cast issues
MONTH_INFO AS (
    SELECT
        EXTRACT(
            DAY FROM (
                DATE_TRUNC('month', CURRENT_DATE)::DATE + INTERVAL '1 month'
                - DATE_TRUNC('month', CURRENT_DATE)::DATE
            )
        )::INTEGER                                                   AS DAYS_IN_MONTH,
        (CURRENT_DATE - DATE_TRUNC('month', CURRENT_DATE)::DATE + 1) AS DAYS_ELAPSED
),

PACE_CALC AS (
    SELECT
        COALESCE(CUR.USER_ID, HIST.USER_ID)    AS USER_ID,
        COALESCE(CUR.CURRENCY, HIST.CURRENCY)  AS CURRENCY,
        COALESCE(CUR.MONTH_SPENDING_SO_FAR, 0) AS MONTH_SPENDING_SO_FAR,

        MON.DAYS_ELAPSED,
        MON.DAYS_IN_MONTH,

        -- Historical average daily spending
        COALESCE(HIST.AVG_DAILY_SPENDING, 0)   AS AVG_DAILY_SPENDING,

        -- Expected spending so far (based on historical daily average * days elapsed)
        COALESCE(HIST.AVG_DAILY_SPENDING, 0)
        * MON.DAYS_ELAPSED                     AS EXPECTED_SPENDING,

        -- Projected month total (daily avg * days in month)
        COALESCE(HIST.AVG_DAILY_SPENDING, 0)
        * MON.DAYS_IN_MONTH                    AS PROJECTED_MONTH_TOTAL

    FROM CURRENT_MONTH_SPENDING AS CUR
    FULL OUTER JOIN HISTORICAL_DAILY AS HIST
        ON CUR.USER_ID = HIST.USER_ID AND CUR.CURRENCY = HIST.CURRENCY
    CROSS JOIN MONTH_INFO AS MON
)

SELECT
    USER_ID,
    CURRENCY,
    MONTH_SPENDING_SO_FAR,
    DAYS_ELAPSED,
    DAYS_IN_MONTH,
    AVG_DAILY_SPENDING,
    ROUND(EXPECTED_SPENDING, 2)                         AS EXPECTED_SPENDING,
    ROUND(PROJECTED_MONTH_TOTAL, 2)                     AS PROJECTED_MONTH_TOTAL,

    -- Pace ratio: actual / expected (> 1 means spending faster)
    CASE
        WHEN EXPECTED_SPENDING > 0
            THEN ROUND(MONTH_SPENDING_SO_FAR / EXPECTED_SPENDING, 2)
    END                                                 AS PACE_RATIO,

    -- Pace status
    CASE
        WHEN AVG_DAILY_SPENDING = 0 THEN 'no_history'
        WHEN EXPECTED_SPENDING > 0 AND MONTH_SPENDING_SO_FAR / EXPECTED_SPENDING <= 0.9
            THEN 'behind'
        WHEN EXPECTED_SPENDING > 0 AND MONTH_SPENDING_SO_FAR / EXPECTED_SPENDING <= 1.1
            THEN 'on_track'
        ELSE 'ahead'
    END                                                 AS PACE_STATUS,

    -- Difference: actual minus expected (positive = overspending)
    ROUND(MONTH_SPENDING_SO_FAR - EXPECTED_SPENDING, 2) AS AMOUNT_DIFFERENCE

FROM PACE_CALC
