-- Pre-aggregated daily spending by tag (including untagged transactions)
-- Aggregates transaction amounts by date and tag for efficient trend analysis
-- Fills in missing dates with zero-value rows to ensure continuous time series
-- Excludes internal transfers (matched pairs: same user, different accounts, same date, opposite amounts)

WITH ALL_TRANSACTIONS AS (
    SELECT
        ID AS TRANSACTION_ID,
        ACCOUNT_ID,
        BOOKING_DATE,
        AMOUNT,
        CURRENCY
    FROM {{ ref("src_unified_transactions") }}
    WHERE BOOKING_DATE IS NOT NULL
),

ACCOUNTS AS (
    SELECT
        ACCOUNT_ID,
        USER_ID
    FROM {{ ref('dim_accounts') }}
),

-- Tag all transactions with user_id for internal transfer matching
TRANSACTIONS_WITH_USER AS (
    SELECT
        TXN.*,
        ACC.USER_ID
    FROM ALL_TRANSACTIONS AS TXN
    INNER JOIN ACCOUNTS AS ACC ON TXN.ACCOUNT_ID = ACC.ACCOUNT_ID
),

-- Identify internal transfer pairs:
-- A negative transaction is an internal transfer if there exists a positive transaction
-- on the same day, same absolute amount, same user, different account
INTERNAL_TRANSFER_IDS AS (
    SELECT DISTINCT OUTGOING.TRANSACTION_ID
    FROM TRANSACTIONS_WITH_USER AS OUTGOING
    WHERE
        OUTGOING.AMOUNT < 0  -- Outgoing (spending side)
        AND EXISTS (
            SELECT 1
            FROM TRANSACTIONS_WITH_USER AS INCOMING
            WHERE
                INCOMING.USER_ID = OUTGOING.USER_ID
                AND INCOMING.ACCOUNT_ID != OUTGOING.ACCOUNT_ID  -- Different account
                AND INCOMING.BOOKING_DATE = OUTGOING.BOOKING_DATE  -- Same day
                AND INCOMING.AMOUNT = -OUTGOING.AMOUNT  -- Opposite amount (positive = incoming)
        )
),

-- Filter to spending transactions, excluding internal transfers
SPENDING_TRANSACTIONS AS (
    SELECT
        SPENDING.TRANSACTION_ID,
        SPENDING.ACCOUNT_ID,
        SPENDING.BOOKING_DATE,
        SPENDING.AMOUNT,
        SPENDING.CURRENCY
    FROM TRANSACTIONS_WITH_USER AS SPENDING
    WHERE
        SPENDING.AMOUNT < 0  -- Only spending
        AND SPENDING.TRANSACTION_ID NOT IN (SELECT ITR.TRANSACTION_ID FROM INTERNAL_TRANSFER_IDS AS ITR)
),

TRANSACTION_SPLITS AS (
    SELECT
        TRANSACTION_ID,
        TAG_ID,
        AMOUNT
    FROM {{ ref("src_unified_transaction_splits") }}
),

TAGS AS (
    SELECT
        ID     AS TAG_ID,
        USER_ID,
        NAME   AS TAG_NAME,
        COLOUR AS TAG_COLOUR
    FROM {{ ref("src_unified_tags") }}
),

-- Identify transactions that have splits (i.e., are tagged)
TRANSACTIONS_WITH_SPLITS AS (
    SELECT DISTINCT TRANSACTION_ID
    FROM TRANSACTION_SPLITS
),

-- For tagged transactions: use split amounts (each split becomes a row with its tag)
SPLIT_TAGGED_TRANSACTIONS AS (
    SELECT
        TXN.TRANSACTION_ID,
        TXN.BOOKING_DATE::DATE AS SPENDING_DATE,
        SPLIT.AMOUNT           AS SPENDING_AMOUNT,  -- Use split amount
        TXN.CURRENCY,
        ACC.USER_ID,
        SPLIT.TAG_ID
    FROM SPENDING_TRANSACTIONS AS TXN
    INNER JOIN ACCOUNTS AS ACC ON TXN.ACCOUNT_ID = ACC.ACCOUNT_ID
    INNER JOIN TRANSACTION_SPLITS AS SPLIT ON TXN.TRANSACTION_ID = SPLIT.TRANSACTION_ID
),

-- For untagged transactions: use full transaction amount with NULL tag
UNTAGGED_TRANSACTIONS AS (
    SELECT
        TXN.TRANSACTION_ID,
        TXN.BOOKING_DATE::DATE AS SPENDING_DATE,
        ABS(TXN.AMOUNT)        AS SPENDING_AMOUNT,
        TXN.CURRENCY,
        ACC.USER_ID,
        NULL::UUID             AS TAG_ID
    FROM SPENDING_TRANSACTIONS AS TXN
    INNER JOIN ACCOUNTS AS ACC ON TXN.ACCOUNT_ID = ACC.ACCOUNT_ID
    WHERE TXN.TRANSACTION_ID NOT IN (SELECT TWS.TRANSACTION_ID FROM TRANSACTIONS_WITH_SPLITS AS TWS)
),

-- Combine tagged and untagged transactions
TAGGED_TRANSACTIONS AS (
    SELECT * FROM SPLIT_TAGGED_TRANSACTIONS
    UNION ALL
    SELECT * FROM UNTAGGED_TRANSACTIONS
),

-- Aggregate actual spending by date, user, tag
ACTUAL_SPENDING AS (
    SELECT
        TAGGED.SPENDING_DATE,
        TAGGED.USER_ID,
        TAGGED.TAG_ID,
        COALESCE(TAG.TAG_NAME, 'Untagged')  AS TAG_NAME,
        COALESCE(TAG.TAG_COLOUR, '#6b7280') AS TAG_COLOUR,
        TAGGED.CURRENCY,
        SUM(TAGGED.SPENDING_AMOUNT)         AS TOTAL_SPENDING,
        COUNT(*)                            AS TRANSACTION_COUNT
    FROM TAGGED_TRANSACTIONS AS TAGGED
    LEFT JOIN TAGS AS TAG ON TAGGED.TAG_ID = TAG.TAG_ID
    GROUP BY
        TAGGED.SPENDING_DATE,
        TAGGED.USER_ID,
        TAGGED.TAG_ID,
        COALESCE(TAG.TAG_NAME, 'Untagged'),
        COALESCE(TAG.TAG_COLOUR, '#6b7280'),
        TAGGED.CURRENCY
),

-- Get date range per user (first and last transaction date)
USER_DATE_RANGE AS (
    SELECT
        USER_ID,
        MIN(SPENDING_DATE) AS MIN_DATE,
        MAX(SPENDING_DATE) AS MAX_DATE
    FROM ACTUAL_SPENDING
    GROUP BY USER_ID
),

-- Generate all dates in each user's range using DuckDB's generate_series
DATE_SPINE AS (
    SELECT
        UDR.USER_ID,
        UNNEST(GENERATE_SERIES(UDR.MIN_DATE, UDR.MAX_DATE, INTERVAL 1 DAY))::DATE AS SPENDING_DATE
    FROM USER_DATE_RANGE AS UDR
),

-- Left join date spine with actual spending to fill gaps
-- For dates with no spending, we create a single row with zeros
FILLED_SPENDING AS (
    SELECT
        DTS.SPENDING_DATE,
        DTS.USER_ID,
        ACTUAL.TAG_ID,
        ACTUAL.TAG_NAME,
        ACTUAL.TAG_COLOUR,
        ACTUAL.CURRENCY,
        ACTUAL.TOTAL_SPENDING,
        ACTUAL.TRANSACTION_COUNT
    FROM DATE_SPINE AS DTS
    LEFT JOIN ACTUAL_SPENDING AS ACTUAL
        ON
            DTS.USER_ID = ACTUAL.USER_ID
            AND DTS.SPENDING_DATE = ACTUAL.SPENDING_DATE
)

-- Return all rows: actual spending OR zero-fill rows for missing dates
-- Zero-fill rows have NULL for tag columns, 0 for spending, 'GBP' for currency
SELECT
    SPENDING_DATE,
    USER_ID,
    TAG_ID,
    COALESCE(TAG_NAME, 'No Spending') AS TAG_NAME,
    COALESCE(TAG_COLOUR, '#6b7280')   AS TAG_COLOUR,
    COALESCE(CURRENCY, 'GBP')         AS CURRENCY,
    COALESCE(TOTAL_SPENDING, 0)       AS TOTAL_SPENDING,
    COALESCE(TRANSACTION_COUNT, 0)    AS TRANSACTION_COUNT
FROM FILLED_SPENDING
