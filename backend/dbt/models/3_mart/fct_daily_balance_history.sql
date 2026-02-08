-- Daily balance history per account
-- Aggregates balance snapshots to daily grain (uses latest snapshot per day)
-- Forward-fills gaps to ensure continuous time series for charting
-- Calculates daily change from previous day

WITH BALANCE_SNAPSHOTS AS (
    SELECT
        ACCOUNT_ID,
        BALANCE_AMOUNT,
        BALANCE_CURRENCY,
        BALANCE_TYPE,
        TOTAL_VALUE,
        UNREALISED_PNL,
        SOURCE_UPDATED_AT,
        CAPTURED_AT,
        CAPTURED_AT::DATE AS BALANCE_DATE
    FROM {{ ref("stg_balance_snapshots") }}
),

ACCOUNTS AS (
    SELECT
        ACCOUNT_ID,
        USER_ID,
        DISPLAY_NAME,
        CURRENCY AS ACCOUNT_CURRENCY,
        ACCOUNT_TYPE
    FROM {{ ref("dim_accounts") }}
),

-- For each day, take the latest snapshot (in case of multiple syncs per day)
RANKED_SNAPSHOTS AS (
    SELECT
        BAL.*,
        ACC.USER_ID,
        ACC.DISPLAY_NAME,
        ACC.ACCOUNT_TYPE,
        ROW_NUMBER() OVER (
            PARTITION BY BAL.ACCOUNT_ID, BAL.BALANCE_DATE
            ORDER BY BAL.CAPTURED_AT DESC
        ) AS ROW_NUM
    FROM BALANCE_SNAPSHOTS AS BAL
    INNER JOIN ACCOUNTS AS ACC ON BAL.ACCOUNT_ID = ACC.ACCOUNT_ID
),

-- Keep only the latest snapshot per account per day
DAILY_SNAPSHOTS AS (
    SELECT
        ACCOUNT_ID,
        USER_ID,
        DISPLAY_NAME,
        ACCOUNT_TYPE,
        BALANCE_DATE,
        BALANCE_AMOUNT,
        BALANCE_CURRENCY,
        BALANCE_TYPE,
        TOTAL_VALUE,
        UNREALISED_PNL,
        SOURCE_UPDATED_AT
    FROM RANKED_SNAPSHOTS
    WHERE ROW_NUM = 1
),

-- Get date range per account (first snapshot date to current date)
-- Extend to CURRENT_DATE so forward-fill works for days without syncs
ACCOUNT_DATE_RANGE AS (
    SELECT
        ACCOUNT_ID,
        MIN(BALANCE_DATE)                         AS MIN_DATE,
        -- Use CURRENT_DATE to ensure we have data up to today for net worth calculations
        GREATEST(MAX(BALANCE_DATE), CURRENT_DATE) AS MAX_DATE
    FROM DAILY_SNAPSHOTS
    GROUP BY ACCOUNT_ID
),

-- Generate all dates in each account's range using DuckDB's generate_series
DATE_SPINE AS (
    SELECT
        ADR.ACCOUNT_ID,
        UNNEST(GENERATE_SERIES(ADR.MIN_DATE, ADR.MAX_DATE, INTERVAL 1 DAY))::DATE AS BALANCE_DATE
    FROM ACCOUNT_DATE_RANGE AS ADR
),

-- Get account metadata for date spine
DATE_SPINE_WITH_METADATA AS (
    SELECT
        DTS.ACCOUNT_ID,
        DTS.BALANCE_DATE,
        ACC.USER_ID,
        ACC.DISPLAY_NAME,
        ACC.ACCOUNT_TYPE,
        ACC.ACCOUNT_CURRENCY
    FROM DATE_SPINE AS DTS
    INNER JOIN ACCOUNTS AS ACC ON DTS.ACCOUNT_ID = ACC.ACCOUNT_ID
),

-- Left join date spine with actual snapshots
JOINED_DATA AS (
    SELECT
        DTS.ACCOUNT_ID,
        DTS.BALANCE_DATE,
        DTS.USER_ID,
        DTS.DISPLAY_NAME,
        DTS.ACCOUNT_TYPE,
        SNAPS.BALANCE_AMOUNT,
        COALESCE(SNAPS.BALANCE_CURRENCY, DTS.ACCOUNT_CURRENCY) AS BALANCE_CURRENCY,
        SNAPS.BALANCE_TYPE,
        SNAPS.TOTAL_VALUE,
        SNAPS.UNREALISED_PNL,
        SNAPS.SOURCE_UPDATED_AT,
        SNAPS.BALANCE_AMOUNT IS NOT NULL                       AS HAS_SNAPSHOT
    FROM DATE_SPINE_WITH_METADATA AS DTS
    LEFT JOIN DAILY_SNAPSHOTS AS SNAPS
        ON
            DTS.ACCOUNT_ID = SNAPS.ACCOUNT_ID
            AND DTS.BALANCE_DATE = SNAPS.BALANCE_DATE
),

-- Forward-fill missing balances (carry forward last known balance)
-- Use a window function to get the last non-null balance
FILLED_DATA AS (
    SELECT
        ACCOUNT_ID,
        BALANCE_DATE,
        USER_ID,
        DISPLAY_NAME,
        ACCOUNT_TYPE,
        -- Forward-fill balance using last known value
        COALESCE(
            BALANCE_AMOUNT,
            LAST_VALUE(BALANCE_AMOUNT IGNORE NULLS) OVER (
                PARTITION BY ACCOUNT_ID
                ORDER BY BALANCE_DATE
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
        ) AS BALANCE_AMOUNT,
        COALESCE(
            BALANCE_CURRENCY,
            LAST_VALUE(BALANCE_CURRENCY IGNORE NULLS) OVER (
                PARTITION BY ACCOUNT_ID
                ORDER BY BALANCE_DATE
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
        ) AS BALANCE_CURRENCY,
        COALESCE(
            BALANCE_TYPE,
            LAST_VALUE(BALANCE_TYPE IGNORE NULLS) OVER (
                PARTITION BY ACCOUNT_ID
                ORDER BY BALANCE_DATE
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
        ) AS BALANCE_TYPE,
        COALESCE(
            TOTAL_VALUE,
            LAST_VALUE(TOTAL_VALUE IGNORE NULLS) OVER (
                PARTITION BY ACCOUNT_ID
                ORDER BY BALANCE_DATE
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
        ) AS TOTAL_VALUE,
        COALESCE(
            UNREALISED_PNL,
            LAST_VALUE(UNREALISED_PNL IGNORE NULLS) OVER (
                PARTITION BY ACCOUNT_ID
                ORDER BY BALANCE_DATE
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
        ) AS UNREALISED_PNL,
        SOURCE_UPDATED_AT,
        HAS_SNAPSHOT
    FROM JOINED_DATA
),

-- Calculate daily change from previous day
WITH_DAILY_CHANGE AS (
    SELECT
        *,
        BALANCE_AMOUNT - LAG(BALANCE_AMOUNT) OVER (
            PARTITION BY ACCOUNT_ID
            ORDER BY BALANCE_DATE
        ) AS DAILY_CHANGE,
        TOTAL_VALUE - LAG(TOTAL_VALUE) OVER (
            PARTITION BY ACCOUNT_ID
            ORDER BY BALANCE_DATE
        ) AS DAILY_VALUE_CHANGE
    FROM FILLED_DATA
)

SELECT
    ACCOUNT_ID,
    USER_ID,
    DISPLAY_NAME                    AS ACCOUNT_NAME,
    ACCOUNT_TYPE,
    BALANCE_DATE,
    BALANCE_AMOUNT,
    BALANCE_CURRENCY,
    BALANCE_TYPE,
    TOTAL_VALUE,
    UNREALISED_PNL,
    COALESCE(DAILY_CHANGE, 0)       AS DAILY_CHANGE,
    COALESCE(DAILY_VALUE_CHANGE, 0) AS DAILY_VALUE_CHANGE,
    HAS_SNAPSHOT                    AS IS_ACTUAL_SNAPSHOT
FROM WITH_DAILY_CHANGE
WHERE BALANCE_AMOUNT IS NOT NULL  -- Exclude rows where we have no data yet
ORDER BY ACCOUNT_ID, BALANCE_DATE
