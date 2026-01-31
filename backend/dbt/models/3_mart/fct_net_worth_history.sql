-- Net worth history per user per day
-- Sums all account balances to calculate total net worth over time
-- Includes daily change, 7-day rolling average, and month comparison metrics

WITH DAILY_BALANCES AS (
    -- Get balance history from fct_daily_balance_history
    SELECT
        USER_ID,
        BALANCE_DATE,
        ACCOUNT_ID,
        ACCOUNT_NAME,
        ACCOUNT_TYPE,
        BALANCE_AMOUNT,
        BALANCE_CURRENCY,
        TOTAL_VALUE,
        IS_ACTUAL_SNAPSHOT
    FROM {{ ref("fct_daily_balance_history") }}
),

-- Aggregate all accounts per user per day
-- Use TOTAL_VALUE for investment accounts, BALANCE_AMOUNT for bank accounts
DAILY_NET_WORTH AS (
    SELECT
        USER_ID,
        BALANCE_DATE,
        BALANCE_CURRENCY             AS CURRENCY,
        -- Sum balance_amount for all accounts (bank account balance or cash for investment)
        SUM(BALANCE_AMOUNT)          AS TOTAL_CASH_BALANCE,
        -- Sum total_value for investment accounts (null for bank accounts)
        SUM(TOTAL_VALUE)             AS TOTAL_INVESTMENT_VALUE,
        -- Net worth = cash balances + investment values
        -- For bank accounts: balance_amount is the value
        -- For investment accounts: total_value is the full portfolio value
        SUM(
            CASE
                WHEN ACCOUNT_TYPE = 'trading' AND TOTAL_VALUE IS NOT NULL
                    THEN TOTAL_VALUE
                ELSE BALANCE_AMOUNT
            END
        )                            AS NET_WORTH,
        COUNT(DISTINCT ACCOUNT_ID)   AS ACCOUNT_COUNT,
        -- Track if all accounts have actual snapshots (not gap-filled)
        BOOL_AND(IS_ACTUAL_SNAPSHOT) AS ALL_ACTUAL_SNAPSHOTS
    FROM DAILY_BALANCES
    GROUP BY USER_ID, BALANCE_DATE, BALANCE_CURRENCY
),

-- Calculate daily change and rolling metrics
WITH_METRICS AS (
    SELECT
        USER_ID,
        BALANCE_DATE,
        CURRENCY,
        NET_WORTH,
        TOTAL_CASH_BALANCE,
        TOTAL_INVESTMENT_VALUE,
        ACCOUNT_COUNT,
        ALL_ACTUAL_SNAPSHOTS,
        -- Daily change from previous day
        NET_WORTH - LAG(NET_WORTH) OVER (
            PARTITION BY USER_ID
            ORDER BY BALANCE_DATE
        )                                       AS DAILY_CHANGE,
        -- 7-day rolling average
        AVG(NET_WORTH) OVER (
            PARTITION BY USER_ID
            ORDER BY BALANCE_DATE
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        )                                       AS ROLLING_7D_AVG,
        -- First day of current month for month-start comparison
        DATE_TRUNC('month', BALANCE_DATE)::DATE AS MONTH_START
    FROM DAILY_NET_WORTH
),

-- Get month-start values for comparison
MONTH_START_VALUES AS (
    SELECT
        USER_ID,
        MONTH_START,
        FIRST_VALUE(NET_WORTH) OVER (
            PARTITION BY USER_ID, MONTH_START
            ORDER BY BALANCE_DATE
        ) AS MONTH_START_NET_WORTH
    FROM WITH_METRICS
),

-- Join month-start values back
FINAL AS (
    SELECT
        MET.USER_ID,
        MET.BALANCE_DATE,
        MET.CURRENCY,
        MET.NET_WORTH,
        MET.TOTAL_CASH_BALANCE,
        MET.TOTAL_INVESTMENT_VALUE,
        MET.ACCOUNT_COUNT,
        MET.ALL_ACTUAL_SNAPSHOTS,
        COALESCE(MET.DAILY_CHANGE, 0)             AS DAILY_CHANGE,
        MET.ROLLING_7D_AVG,
        MET.MONTH_START,
        MSV.MONTH_START_NET_WORTH,
        MET.NET_WORTH - MSV.MONTH_START_NET_WORTH AS CHANGE_FROM_MONTH_START,
        -- Percentage change from month start
        CASE
            WHEN MSV.MONTH_START_NET_WORTH != 0
                THEN ((MET.NET_WORTH - MSV.MONTH_START_NET_WORTH) / MSV.MONTH_START_NET_WORTH) * 100
            ELSE 0
        END                                       AS PCT_CHANGE_FROM_MONTH_START
    FROM WITH_METRICS AS MET
    LEFT JOIN MONTH_START_VALUES AS MSV
        ON
            MET.USER_ID = MSV.USER_ID
            AND MET.MONTH_START = MSV.MONTH_START
)

SELECT
    USER_ID,
    BALANCE_DATE,
    CURRENCY,
    NET_WORTH,
    TOTAL_CASH_BALANCE,
    TOTAL_INVESTMENT_VALUE,
    ACCOUNT_COUNT,
    ALL_ACTUAL_SNAPSHOTS AS IS_ACTUAL_SNAPSHOT,
    DAILY_CHANGE,
    ROLLING_7D_AVG,
    MONTH_START,
    MONTH_START_NET_WORTH,
    CHANGE_FROM_MONTH_START,
    PCT_CHANGE_FROM_MONTH_START
FROM FINAL
ORDER BY USER_ID, BALANCE_DATE
