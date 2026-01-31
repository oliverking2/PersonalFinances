-- Intermediate model for detecting recurring transaction patterns
-- Groups transactions by merchant and calculates pattern candidates
-- This model identifies potential subscriptions, recurring payments, and income

WITH MERCHANT_GROUPS AS (
    -- Group transactions by normalised merchant name, amount bucket, AND direction
    -- Amount bucket separates different subscription tiers (e.g., Apple £4.99 vs £2.99)
    -- Direction separates income from expenses for the same counterparty
    SELECT
        TXN.ACCOUNT_ID,
        ACC.USER_ID,
        -- Normalise merchant name:
        -- 1. Use counterparty_name if available, otherwise description
        -- 2. Strip trailing dates (YYYY-MM-DD) that make each transaction unique
        -- 3. Lowercase and trim
        LOWER(TRIM(REGEXP_REPLACE(
            COALESCE(TXN.COUNTERPARTY_NAME, TXN.DESCRIPTION),
            '\s*\d{4}-\d{2}-\d{2}$',
            ''
        )))                                                       AS MERCHANT_NAME,
        -- Direction: expense (negative amounts) or income (positive amounts)
        CASE WHEN TXN.AMOUNT < 0 THEN 'expense' ELSE 'income' END AS DIRECTION,
        -- Graded rounding for amount buckets:
        -- Under £10: nearest £1 (separates £2.99 vs £4.99)
        -- £10-50: nearest £5
        -- £50-200: nearest £10
        -- £200+: nearest £25 (allows variance in large bills like £321)
        CASE
            WHEN ABS(TXN.AMOUNT) < 10 THEN ROUND(ABS(TXN.AMOUNT))
            WHEN ABS(TXN.AMOUNT) < 50 THEN ROUND(ABS(TXN.AMOUNT) / 5) * 5
            WHEN ABS(TXN.AMOUNT) < 200 THEN ROUND(ABS(TXN.AMOUNT) / 10) * 10
            ELSE ROUND(ABS(TXN.AMOUNT) / 25) * 25
        END                                                       AS AMOUNT_BUCKET,
        -- Combine merchant + direction + amount bucket as the pattern key
        -- Direction included to separate income from expense for same counterparty
        LOWER(TRIM(REGEXP_REPLACE(
            COALESCE(TXN.COUNTERPARTY_NAME, TXN.DESCRIPTION),
            '\s*\d{4}-\d{2}-\d{2}$',
            ''
        )))
        || '_' || CASE WHEN TXN.AMOUNT < 0 THEN 'exp' ELSE 'inc' END
        || '_£' || CAST(
            CASE
                WHEN ABS(TXN.AMOUNT) < 10 THEN ROUND(ABS(TXN.AMOUNT))
                WHEN ABS(TXN.AMOUNT) < 50 THEN ROUND(ABS(TXN.AMOUNT) / 5) * 5
                WHEN ABS(TXN.AMOUNT) < 200 THEN ROUND(ABS(TXN.AMOUNT) / 10) * 10
                ELSE ROUND(ABS(TXN.AMOUNT) / 25) * 25
            END AS VARCHAR
        )                                                         AS MERCHANT_KEY,
        TXN.TRANSACTION_ID,
        TXN.BOOKING_DATE,
        TXN.AMOUNT,
        TXN.CURRENCY,
        ROW_NUMBER() OVER (
            PARTITION BY
                TXN.ACCOUNT_ID,
                LOWER(TRIM(REGEXP_REPLACE(
                    COALESCE(TXN.COUNTERPARTY_NAME, TXN.DESCRIPTION),
                    '\s*\d{4}-\d{2}-\d{2}$',
                    ''
                ))),
                CASE WHEN TXN.AMOUNT < 0 THEN 'expense' ELSE 'income' END,
                CASE
                    WHEN ABS(TXN.AMOUNT) < 10 THEN ROUND(ABS(TXN.AMOUNT))
                    WHEN ABS(TXN.AMOUNT) < 50 THEN ROUND(ABS(TXN.AMOUNT) / 5) * 5
                    WHEN ABS(TXN.AMOUNT) < 200 THEN ROUND(ABS(TXN.AMOUNT) / 10) * 10
                    ELSE ROUND(ABS(TXN.AMOUNT) / 25) * 25
                END
            ORDER BY TXN.BOOKING_DATE
        )                                                         AS OCCURRENCE_NUM
    FROM {{ ref('fct_transactions') }} AS TXN
    INNER JOIN {{ ref('dim_accounts') }} AS ACC ON TXN.ACCOUNT_ID = ACC.ACCOUNT_ID
    WHERE
        TXN.BOOKING_DATE >= CURRENT_DATE - INTERVAL '18 months'
        AND COALESCE(TXN.COUNTERPARTY_NAME, TXN.DESCRIPTION) IS NOT NULL
),

WITH_INTERVALS AS (
    -- Calculate intervals between consecutive transactions
    SELECT
        GRP.*,
        LAG(GRP.BOOKING_DATE) OVER (
            PARTITION BY GRP.ACCOUNT_ID, GRP.MERCHANT_KEY
            ORDER BY GRP.BOOKING_DATE
        ) AS PREV_DATE,
        DATE_DIFF(
            'day',
            LAG(GRP.BOOKING_DATE) OVER (
                PARTITION BY GRP.ACCOUNT_ID, GRP.MERCHANT_KEY
                ORDER BY GRP.BOOKING_DATE
            ),
            GRP.BOOKING_DATE
        ) AS INTERVAL_DAYS
    FROM MERCHANT_GROUPS AS GRP
),

MERCHANT_STATS AS (
    -- Calculate statistics per merchant (including direction)
    SELECT
        ACCOUNT_ID,
        USER_ID,
        MERCHANT_KEY,
        -- Clean merchant name for display (without £xxx suffix)
        MAX(MERCHANT_NAME)    AS MERCHANT_NAME,
        -- Carry direction through (all rows in group have same direction)
        MAX(DIRECTION)        AS DIRECTION,
        CURRENCY,
        COUNT(*)              AS OCCURRENCE_COUNT,
        MIN(AMOUNT)           AS MIN_AMOUNT,
        MAX(AMOUNT)           AS MAX_AMOUNT,
        AVG(AMOUNT)           AS AVG_AMOUNT,
        STDDEV(AMOUNT)        AS AMOUNT_STDDEV,
        AVG(INTERVAL_DAYS)    AS AVG_INTERVAL,
        STDDEV(INTERVAL_DAYS) AS INTERVAL_STDDEV,
        MAX(BOOKING_DATE)     AS LAST_OCCURRENCE,
        MIN(BOOKING_DATE)     AS FIRST_OCCURRENCE,
        -- Aggregate transaction IDs for linking
        LIST(TRANSACTION_ID)  AS TRANSACTION_IDS
    FROM WITH_INTERVALS
    WHERE INTERVAL_DAYS IS NOT NULL
    GROUP BY ACCOUNT_ID, USER_ID, MERCHANT_KEY, CURRENCY
    HAVING COUNT(*) >= 2  -- Minimum 2 occurrences for a pattern
),

-- Get the latest transaction amount for each pattern
LATEST_AMOUNTS AS (
    SELECT DISTINCT ON (ACCOUNT_ID, MERCHANT_KEY)
        ACCOUNT_ID,
        MERCHANT_KEY,
        AMOUNT AS LATEST_AMOUNT
    FROM WITH_INTERVALS
    ORDER BY ACCOUNT_ID ASC, MERCHANT_KEY ASC, BOOKING_DATE DESC
)

SELECT
    STS.ACCOUNT_ID,
    STS.USER_ID,
    STS.MERCHANT_KEY,
    STS.MERCHANT_NAME,
    STS.DIRECTION,
    STS.CURRENCY,
    STS.OCCURRENCE_COUNT,
    STS.MIN_AMOUNT,
    STS.MAX_AMOUNT,
    STS.AVG_AMOUNT,
    -- Use latest transaction amount as expected amount (reflects current price)
    LAT.LATEST_AMOUNT,
    STS.AMOUNT_STDDEV,
    STS.AVG_INTERVAL,
    STS.INTERVAL_STDDEV,
    STS.LAST_OCCURRENCE,
    STS.FIRST_OCCURRENCE,
    -- Transaction IDs that belong to this pattern (for linking)
    STS.TRANSACTION_IDS,
    -- Detect frequency from average interval (in days) with tolerance for real-world variation
    -- Ranges are wider than exact intervals because:
    -- - Payment processing can delay transactions by 1-3 days
    -- - Weekends/holidays shift payment dates
    -- - Some merchants have variable billing cycles
    CASE
        WHEN STS.AVG_INTERVAL BETWEEN 5 AND 10 THEN 'weekly'      -- 7 days ± 2-3 day tolerance
        WHEN STS.AVG_INTERVAL BETWEEN 12 AND 20 THEN 'fortnightly' -- 14 days ± 2-6 day tolerance
        WHEN STS.AVG_INTERVAL BETWEEN 25 AND 38 THEN 'monthly'    -- ~30 days ± 5-8 day tolerance
        WHEN STS.AVG_INTERVAL BETWEEN 75 AND 105 THEN 'quarterly' -- ~90 days ± 15 day tolerance
        WHEN STS.AVG_INTERVAL BETWEEN 330 AND 400 THEN 'annual'   -- ~365 days ± 35 day tolerance
        ELSE 'irregular'
    END AS DETECTED_FREQUENCY,
    -- Calculate confidence score using weighted average (not multiplication)
    -- This prevents one weak factor from destroying the whole score
    -- Weights: occurrences=20%, interval consistency=30%, amount consistency=50%
    -- Occurrence: max at 4 (not 3) to reward longer history
    -- Interval: tolerance 0.35 (more forgiving than 0.5)
    -- Amount: higher weight (50%) for consistent pricing, tolerance 0.15
    LEAST(
        1.0,
        (0.20 * LEAST(1.0, CAST(STS.OCCURRENCE_COUNT AS DOUBLE) / 4.0))
        + (0.30 * (1.0 - LEAST(1.0, COALESCE(STS.INTERVAL_STDDEV, 0) / NULLIF(STS.AVG_INTERVAL, 0) / 0.35)))
        + (0.50 * (1.0 - LEAST(1.0, COALESCE(STS.AMOUNT_STDDEV, 0) / NULLIF(ABS(STS.AVG_AMOUNT), 0) / 0.15)))
    )   AS CONFIDENCE_SCORE,
    -- Calculate amount variance as percentage
    CASE
        WHEN STS.AVG_AMOUNT != 0
            THEN
                ABS((STS.MAX_AMOUNT - STS.MIN_AMOUNT) / STS.AVG_AMOUNT) * 100
        ELSE 0
    END AS AMOUNT_VARIANCE_PCT
FROM MERCHANT_STATS AS STS
INNER JOIN LATEST_AMOUNTS AS LAT
    ON STS.ACCOUNT_ID = LAT.ACCOUNT_ID AND STS.MERCHANT_KEY = LAT.MERCHANT_KEY
WHERE STS.AVG_INTERVAL BETWEEN 5 AND 400  -- Filter out very irregular patterns
