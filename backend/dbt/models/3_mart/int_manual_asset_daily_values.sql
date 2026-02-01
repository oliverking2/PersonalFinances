-- Daily value history for manual assets
-- Aggregates value snapshots to daily grain (uses latest snapshot per day)
-- Forward-fills gaps to ensure continuous time series for charting
-- Used to integrate manual assets into net worth calculations

WITH MANUAL_ASSETS AS (
    -- Get active manual assets with their metadata
    SELECT
        ID   AS ASSET_ID,
        USER_ID,
        NAME AS ASSET_NAME,
        ASSET_TYPE,
        CUSTOM_TYPE,
        IS_LIABILITY,
        CURRENCY
    FROM {{ ref("src_manual_assets") }}
),

VALUE_SNAPSHOTS AS (
    -- Get all value snapshots
    SELECT
        ASSET_ID,
        VALUE             AS ASSET_VALUE,
        CURRENCY,
        CAPTURED_AT,
        CAPTURED_AT::DATE AS VALUE_DATE
    FROM {{ ref("src_manual_asset_value_snapshots") }}
),

-- For each day, take the latest snapshot (in case of multiple updates per day)
RANKED_SNAPSHOTS AS (
    SELECT
        SNAP.*,
        ASSETS.USER_ID,
        ASSETS.ASSET_NAME,
        ASSETS.ASSET_TYPE,
        ASSETS.IS_LIABILITY,
        ROW_NUMBER() OVER (
            PARTITION BY SNAP.ASSET_ID, SNAP.VALUE_DATE
            ORDER BY SNAP.CAPTURED_AT DESC
        ) AS ROW_NUM
    FROM VALUE_SNAPSHOTS AS SNAP
    INNER JOIN MANUAL_ASSETS AS ASSETS ON SNAP.ASSET_ID = ASSETS.ASSET_ID
),

-- Keep only the latest snapshot per asset per day
DAILY_SNAPSHOTS AS (
    SELECT
        ASSET_ID,
        USER_ID,
        ASSET_NAME,
        ASSET_TYPE,
        IS_LIABILITY,
        VALUE_DATE,
        ASSET_VALUE,
        CURRENCY
    FROM RANKED_SNAPSHOTS
    WHERE ROW_NUM = 1
),

-- Get date range per asset (first and last snapshot date)
ASSET_DATE_RANGE AS (
    SELECT
        ASSET_ID,
        MIN(VALUE_DATE) AS MIN_DATE,
        MAX(VALUE_DATE) AS MAX_DATE
    FROM DAILY_SNAPSHOTS
    GROUP BY ASSET_ID
),

-- Generate all dates in each asset's range using DuckDB's generate_series
DATE_SPINE AS (
    SELECT
        ADR.ASSET_ID,
        UNNEST(GENERATE_SERIES(ADR.MIN_DATE, ADR.MAX_DATE, INTERVAL 1 DAY))::DATE AS VALUE_DATE
    FROM ASSET_DATE_RANGE AS ADR
),

-- Get asset metadata for date spine
DATE_SPINE_WITH_METADATA AS (
    SELECT
        DTS.ASSET_ID,
        DTS.VALUE_DATE,
        ASSETS.USER_ID,
        ASSETS.ASSET_NAME,
        ASSETS.ASSET_TYPE,
        ASSETS.IS_LIABILITY,
        ASSETS.CURRENCY
    FROM DATE_SPINE AS DTS
    INNER JOIN MANUAL_ASSETS AS ASSETS ON DTS.ASSET_ID = ASSETS.ASSET_ID
),

-- Left join date spine with actual snapshots
JOINED_DATA AS (
    SELECT
        DTS.ASSET_ID,
        DTS.VALUE_DATE,
        DTS.USER_ID,
        DTS.ASSET_NAME,
        DTS.ASSET_TYPE,
        DTS.IS_LIABILITY,
        SNAPS.ASSET_VALUE,
        COALESCE(SNAPS.CURRENCY, DTS.CURRENCY) AS CURRENCY,
        SNAPS.ASSET_VALUE IS NOT NULL          AS HAS_SNAPSHOT
    FROM DATE_SPINE_WITH_METADATA AS DTS
    LEFT JOIN DAILY_SNAPSHOTS AS SNAPS
        ON
            DTS.ASSET_ID = SNAPS.ASSET_ID
            AND DTS.VALUE_DATE = SNAPS.VALUE_DATE
),

-- Forward-fill missing values (carry forward last known value)
FILLED_DATA AS (
    SELECT
        ASSET_ID,
        VALUE_DATE,
        USER_ID,
        ASSET_NAME,
        ASSET_TYPE,
        IS_LIABILITY,
        -- Forward-fill value using last known value
        COALESCE(
            ASSET_VALUE,
            LAST_VALUE(ASSET_VALUE IGNORE NULLS) OVER (
                PARTITION BY ASSET_ID
                ORDER BY VALUE_DATE
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
        ) AS ASSET_VALUE,
        COALESCE(
            CURRENCY,
            LAST_VALUE(CURRENCY IGNORE NULLS) OVER (
                PARTITION BY ASSET_ID
                ORDER BY VALUE_DATE
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
        ) AS CURRENCY,
        HAS_SNAPSHOT
    FROM JOINED_DATA
)

SELECT
    ASSET_ID,
    USER_ID,
    ASSET_NAME,
    ASSET_TYPE,
    IS_LIABILITY,
    VALUE_DATE,
    ASSET_VALUE,
    CURRENCY,
    HAS_SNAPSHOT AS IS_ACTUAL_SNAPSHOT
FROM FILLED_DATA
WHERE ASSET_VALUE IS NOT NULL  -- Exclude rows where we have no data yet
ORDER BY ASSET_ID, VALUE_DATE
