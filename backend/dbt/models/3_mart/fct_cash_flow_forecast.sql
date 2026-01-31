-- Cash flow forecast model
-- Projects future balances based on recurring patterns and planned transactions
-- Combines detected income/expenses with user-defined planned transactions
-- 90-day forward projection by default

-- Configuration for forecast horizon
{% set forecast_days = 90 %}

WITH CURRENT_NET_WORTH AS (
    -- Get the latest net worth for each user as starting point
    SELECT
        USER_ID,
        NET_WORTH    AS STARTING_BALANCE,
        CURRENCY,
        BALANCE_DATE AS AS_OF_DATE
    FROM {{ ref('fct_net_worth_history') }}
    QUALIFY ROW_NUMBER() OVER (PARTITION BY USER_ID ORDER BY BALANCE_DATE DESC) = 1
),

-- Generate date spine for forecast period
FORECAST_DATES AS (
    SELECT CURRENT_DATE + (DATES_SEQ.DAY_OFFSET * INTERVAL '1 day') AS FORECAST_DATE
    FROM (
        SELECT UNNEST(GENERATE_SERIES(0, {{ forecast_days }} - 1)) AS DAY_OFFSET
    ) AS DATES_SEQ
),

-- All recurring patterns (both income and expenses)
RECURRING_CASH_FLOWS AS (
    SELECT
        USER_ID,
        PATTERN_ID,
        DISPLAY_NAME,
        DIRECTION,
        -- Keep actual sign: income positive, expense negative
        CASE
            WHEN DIRECTION = 'income' THEN ABS(EXPECTED_AMOUNT)
            ELSE -ABS(EXPECTED_AMOUNT)
        END         AS AMOUNT,
        CURRENCY,
        FREQUENCY,
        NEXT_EXPECTED_DATE,
        'recurring' AS SOURCE_TYPE
    FROM {{ ref('fct_recurring_patterns') }}
    WHERE
        STATUS NOT IN ('dismissed', 'paused')
        AND NEXT_EXPECTED_DATE IS NOT NULL
),

-- Planned transactions (user-defined income and expenses)
PLANNED_CASH_FLOWS AS (
    SELECT
        USER_ID,
        ID                                                    AS TRANSACTION_ID,
        NAME                                                  AS DISPLAY_NAME,
        CASE WHEN AMOUNT > 0 THEN 'income' ELSE 'expense' END AS DIRECTION,
        AMOUNT,  -- Already signed correctly
        CURRENCY,
        FREQUENCY,
        NEXT_EXPECTED_DATE,
        END_DATE,
        'planned'                                             AS SOURCE_TYPE
    FROM {{ ref('src_planned_transactions') }}
    WHERE
        ENABLED = TRUE
        AND NEXT_EXPECTED_DATE IS NOT NULL
        AND (END_DATE IS NULL OR END_DATE >= CURRENT_DATE)
),

-- Generate all expected occurrences for recurring patterns within forecast period
RECURRING_OCCURRENCES AS (
    SELECT
        RCF.USER_ID,
        RCF.PATTERN_ID        AS SOURCE_ID,
        RCF.DISPLAY_NAME,
        RCF.DIRECTION,
        RCF.AMOUNT,
        RCF.CURRENCY,
        RCF.SOURCE_TYPE,
        F_DATES.FORECAST_DATE AS EXPECTED_DATE
    FROM RECURRING_CASH_FLOWS AS RCF
    CROSS JOIN FORECAST_DATES AS F_DATES
    WHERE
        -- Match frequency to forecast date
        CASE RCF.FREQUENCY
            WHEN 'weekly'
                THEN
                    -- Same day of week as next_expected_date, within forecast
                    DATE_DIFF('day', RCF.NEXT_EXPECTED_DATE, F_DATES.FORECAST_DATE) >= 0
                    AND DATE_DIFF('day', RCF.NEXT_EXPECTED_DATE, F_DATES.FORECAST_DATE) % 7 = 0
            WHEN 'fortnightly'
                THEN
                    DATE_DIFF('day', RCF.NEXT_EXPECTED_DATE, F_DATES.FORECAST_DATE) >= 0
                    AND DATE_DIFF('day', RCF.NEXT_EXPECTED_DATE, F_DATES.FORECAST_DATE) % 14 = 0
            WHEN 'monthly'
                THEN
                    -- Same day of month
                    EXTRACT('day' FROM RCF.NEXT_EXPECTED_DATE) = EXTRACT('day' FROM F_DATES.FORECAST_DATE)
                    AND F_DATES.FORECAST_DATE >= RCF.NEXT_EXPECTED_DATE
            WHEN 'quarterly'
                THEN
                    -- Same day, every 3 months
                    EXTRACT('day' FROM RCF.NEXT_EXPECTED_DATE) = EXTRACT('day' FROM F_DATES.FORECAST_DATE)
                    AND DATE_DIFF('month', RCF.NEXT_EXPECTED_DATE, F_DATES.FORECAST_DATE) >= 0
                    AND DATE_DIFF('month', RCF.NEXT_EXPECTED_DATE, F_DATES.FORECAST_DATE) % 3 = 0
            WHEN 'annual'
                THEN
                    -- Same day and month
                    EXTRACT('day' FROM RCF.NEXT_EXPECTED_DATE) = EXTRACT('day' FROM F_DATES.FORECAST_DATE)
                    AND EXTRACT('month' FROM RCF.NEXT_EXPECTED_DATE) = EXTRACT('month' FROM F_DATES.FORECAST_DATE)
                    AND F_DATES.FORECAST_DATE >= RCF.NEXT_EXPECTED_DATE
            ELSE FALSE
        END
),

-- Generate occurrences for planned transactions
PLANNED_OCCURRENCES AS (
    -- One-time transactions
    SELECT
        PCF.USER_ID,
        PCF.TRANSACTION_ID     AS SOURCE_ID,
        PCF.DISPLAY_NAME,
        PCF.DIRECTION,
        PCF.AMOUNT,
        PCF.CURRENCY,
        PCF.SOURCE_TYPE,
        PCF.NEXT_EXPECTED_DATE AS EXPECTED_DATE
    FROM PLANNED_CASH_FLOWS AS PCF
    WHERE
        PCF.FREQUENCY IS NULL
        AND PCF.NEXT_EXPECTED_DATE BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '{{ forecast_days }} days'

    UNION ALL

    -- Recurring planned transactions
    SELECT
        PCF.USER_ID,
        PCF.TRANSACTION_ID    AS SOURCE_ID,
        PCF.DISPLAY_NAME,
        PCF.DIRECTION,
        PCF.AMOUNT,
        PCF.CURRENCY,
        PCF.SOURCE_TYPE,
        F_DATES.FORECAST_DATE AS EXPECTED_DATE
    FROM PLANNED_CASH_FLOWS AS PCF
    CROSS JOIN FORECAST_DATES AS F_DATES
    WHERE
        PCF.FREQUENCY IS NOT NULL
        AND (PCF.END_DATE IS NULL OR F_DATES.FORECAST_DATE <= PCF.END_DATE)
        AND CASE PCF.FREQUENCY
            WHEN 'weekly'
                THEN
                    DATE_DIFF('day', PCF.NEXT_EXPECTED_DATE, F_DATES.FORECAST_DATE) >= 0
                    AND DATE_DIFF('day', PCF.NEXT_EXPECTED_DATE, F_DATES.FORECAST_DATE) % 7 = 0
            WHEN 'fortnightly'
                THEN
                    DATE_DIFF('day', PCF.NEXT_EXPECTED_DATE, F_DATES.FORECAST_DATE) >= 0
                    AND DATE_DIFF('day', PCF.NEXT_EXPECTED_DATE, F_DATES.FORECAST_DATE) % 14 = 0
            WHEN 'monthly'
                THEN
                    EXTRACT('day' FROM PCF.NEXT_EXPECTED_DATE) = EXTRACT('day' FROM F_DATES.FORECAST_DATE)
                    AND F_DATES.FORECAST_DATE >= PCF.NEXT_EXPECTED_DATE
            WHEN 'quarterly'
                THEN
                    EXTRACT('day' FROM PCF.NEXT_EXPECTED_DATE) = EXTRACT('day' FROM F_DATES.FORECAST_DATE)
                    AND DATE_DIFF('month', PCF.NEXT_EXPECTED_DATE, F_DATES.FORECAST_DATE) >= 0
                    AND DATE_DIFF('month', PCF.NEXT_EXPECTED_DATE, F_DATES.FORECAST_DATE) % 3 = 0
            WHEN 'annual'
                THEN
                    EXTRACT('day' FROM PCF.NEXT_EXPECTED_DATE) = EXTRACT('day' FROM F_DATES.FORECAST_DATE)
                    AND EXTRACT('month' FROM PCF.NEXT_EXPECTED_DATE) = EXTRACT('month' FROM F_DATES.FORECAST_DATE)
                    AND F_DATES.FORECAST_DATE >= PCF.NEXT_EXPECTED_DATE
            ELSE FALSE
        END
),

-- Combine all cash flow events
ALL_CASH_FLOWS AS (
    SELECT * FROM RECURRING_OCCURRENCES
    UNION ALL
    SELECT * FROM PLANNED_OCCURRENCES
),

-- Aggregate daily totals by user
DAILY_TOTALS AS (
    SELECT
        USER_ID,
        EXPECTED_DATE                                                    AS FORECAST_DATE,
        SUM(AMOUNT)                                                      AS DAILY_CHANGE,
        SUM(CASE WHEN DIRECTION = 'income' THEN AMOUNT ELSE 0 END)       AS DAILY_INCOME,
        SUM(CASE WHEN DIRECTION = 'expense' THEN ABS(AMOUNT) ELSE 0 END) AS DAILY_EXPENSES,
        COUNT(*)                                                         AS EVENT_COUNT
    FROM ALL_CASH_FLOWS
    GROUP BY USER_ID, EXPECTED_DATE
),

-- Create full date spine per user (including days with no events)
USER_DATE_SPINE AS (
    SELECT
        CNW.USER_ID,
        F_DATES.FORECAST_DATE,
        CNW.STARTING_BALANCE,
        CNW.CURRENCY,
        CNW.AS_OF_DATE
    FROM CURRENT_NET_WORTH AS CNW
    CROSS JOIN FORECAST_DATES AS F_DATES
),

-- Join daily totals to date spine
FORECAST_WITH_EVENTS AS (
    SELECT
        UDS.USER_ID,
        UDS.FORECAST_DATE,
        UDS.STARTING_BALANCE,
        UDS.CURRENCY,
        UDS.AS_OF_DATE,
        COALESCE(DAY_TOTALS.DAILY_CHANGE, 0)   AS DAILY_CHANGE,
        COALESCE(DAY_TOTALS.DAILY_INCOME, 0)   AS DAILY_INCOME,
        COALESCE(DAY_TOTALS.DAILY_EXPENSES, 0) AS DAILY_EXPENSES,
        COALESCE(DAY_TOTALS.EVENT_COUNT, 0)    AS EVENT_COUNT
    FROM USER_DATE_SPINE AS UDS
    LEFT JOIN DAILY_TOTALS AS DAY_TOTALS
        ON UDS.USER_ID = DAY_TOTALS.USER_ID AND UDS.FORECAST_DATE = DAY_TOTALS.FORECAST_DATE
),

-- Calculate cumulative balance
WITH_CUMULATIVE AS (
    SELECT
        USER_ID,
        FORECAST_DATE,
        STARTING_BALANCE,
        CURRENCY,
        AS_OF_DATE,
        DAILY_CHANGE,
        DAILY_INCOME,
        DAILY_EXPENSES,
        EVENT_COUNT,
        -- Cumulative change from start
        SUM(DAILY_CHANGE) OVER (
            PARTITION BY USER_ID
            ORDER BY FORECAST_DATE
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS CUMULATIVE_CHANGE,
        -- Projected balance
        STARTING_BALANCE + SUM(DAILY_CHANGE) OVER (
            PARTITION BY USER_ID
            ORDER BY FORECAST_DATE
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS PROJECTED_BALANCE
    FROM FORECAST_WITH_EVENTS
)

SELECT
    USER_ID,
    FORECAST_DATE,
    CURRENCY,
    STARTING_BALANCE,
    AS_OF_DATE,
    DAILY_CHANGE,
    DAILY_INCOME,
    DAILY_EXPENSES,
    EVENT_COUNT,
    CUMULATIVE_CHANGE,
    PROJECTED_BALANCE,
    -- Days from today
    DATE_DIFF('day', CURRENT_DATE, FORECAST_DATE)           AS DAYS_FROM_NOW,
    -- Week number in forecast
    (DATE_DIFF('day', CURRENT_DATE, FORECAST_DATE) / 7) + 1 AS FORECAST_WEEK
FROM WITH_CUMULATIVE
ORDER BY USER_ID, FORECAST_DATE
