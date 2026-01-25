-- Pre-aggregated daily spending by tag
-- Aggregates transaction amounts by date and tag for efficient trend analysis

WITH TRANSACTIONS AS (
    SELECT
        ID AS TRANSACTION_ID,
        ACCOUNT_ID,
        BOOKING_DATE,
        AMOUNT,
        CURRENCY
    FROM {{ ref("src_unified_transactions") }}
    WHERE
        BOOKING_DATE IS NOT NULL
        AND AMOUNT < 0  -- Only spending (negative amounts)
),

TRANSACTION_TAGS AS (
    SELECT
        TRANSACTION_ID,
        TAG_ID
    FROM {{ ref("src_unified_transaction_tags") }}
),

TAGS AS (
    SELECT
        ID     AS TAG_ID,
        USER_ID,
        NAME   AS TAG_NAME,
        COLOUR AS TAG_COLOUR
    FROM {{ ref("src_unified_tags") }}
),

ACCOUNTS AS (
    SELECT
        ACCOUNT_ID,
        USER_ID
    FROM {{ ref('dim_accounts') }}
),

-- Join transactions with their tags
TAGGED_TRANSACTIONS AS (
    SELECT
        TXN.TRANSACTION_ID,
        TXN.BOOKING_DATE::DATE AS SPENDING_DATE,
        ABS(TXN.AMOUNT)        AS SPENDING_AMOUNT,
        TXN.CURRENCY,
        ACC.USER_ID,
        TXN_TAGS.TAG_ID
    FROM TRANSACTIONS AS TXN
    INNER JOIN ACCOUNTS AS ACC ON TXN.ACCOUNT_ID = ACC.ACCOUNT_ID
    INNER JOIN TRANSACTION_TAGS AS TXN_TAGS ON TXN.TRANSACTION_ID = TXN_TAGS.TRANSACTION_ID
)

-- Aggregate by date, user, tag
SELECT
    TAGGED.SPENDING_DATE,
    TAGGED.USER_ID,
    TAGGED.TAG_ID,
    TAG.TAG_NAME,
    TAG.TAG_COLOUR,
    TAGGED.CURRENCY,
    SUM(TAGGED.SPENDING_AMOUNT) AS TOTAL_SPENDING,
    COUNT(*)                    AS TRANSACTION_COUNT
FROM TAGGED_TRANSACTIONS AS TAGGED
INNER JOIN TAGS AS TAG ON TAGGED.TAG_ID = TAG.TAG_ID
GROUP BY
    TAGGED.SPENDING_DATE,
    TAGGED.USER_ID,
    TAGGED.TAG_ID,
    TAG.TAG_NAME,
    TAG.TAG_COLOUR,
    TAGGED.CURRENCY
