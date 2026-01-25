-- Fact table for transactions with tags denormalized
-- Base transaction data enriched with account and tag context for analytics

WITH TRANSACTIONS AS (
    SELECT
        ID AS TRANSACTION_ID,
        ACCOUNT_ID,
        BOOKING_DATE,
        VALUE_DATE,
        AMOUNT,
        CURRENCY,
        COUNTERPARTY_NAME,
        DESCRIPTION,
        CATEGORY,
        SYNCED_AT
    FROM {{ ref("src_unified_transactions") }}
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
        NAME   AS TAG_NAME,
        COLOUR AS TAG_COLOUR
    FROM {{ ref("src_unified_tags") }}
),

-- Aggregate tags per transaction into a list
TAGS_AGG AS (
    SELECT
        TXN_TAGS.TRANSACTION_ID,
        LIST(STRUCT_PACK(
            TAG_ID := TAG.TAG_ID,
            TAG_NAME := TAG.TAG_NAME,
            TAG_COLOUR := TAG.TAG_COLOUR
        )) AS TAGS
    FROM TRANSACTION_TAGS AS TXN_TAGS
    INNER JOIN TAGS AS TAG ON TXN_TAGS.TAG_ID = TAG.TAG_ID
    GROUP BY TXN_TAGS.TRANSACTION_ID
),

ACCOUNTS AS (
    SELECT * FROM {{ ref('dim_accounts') }}
)

SELECT
    TXN.TRANSACTION_ID,
    TXN.ACCOUNT_ID,
    ACC.USER_ID,
    TXN.BOOKING_DATE,
    TXN.VALUE_DATE,
    TXN.AMOUNT,
    TXN.CURRENCY,
    TXN.COUNTERPARTY_NAME,
    TXN.DESCRIPTION,
    TXN.CATEGORY,
    COALESCE(AGG.TAGS, [])                                   AS TAGS,
    ACC.DISPLAY_NAME                                         AS ACCOUNT_NAME,
    ACC.INSTITUTION_NAME,
    -- Spending indicators
    CASE WHEN TXN.AMOUNT < 0 THEN ABS(TXN.AMOUNT) ELSE 0 END AS SPENDING_AMOUNT,
    CASE WHEN TXN.AMOUNT > 0 THEN TXN.AMOUNT ELSE 0 END      AS INCOME_AMOUNT,
    TXN.SYNCED_AT
FROM TRANSACTIONS AS TXN
INNER JOIN ACCOUNTS AS ACC ON TXN.ACCOUNT_ID = ACC.ACCOUNT_ID
LEFT JOIN TAGS_AGG AS AGG ON TXN.TRANSACTION_ID = AGG.TRANSACTION_ID
