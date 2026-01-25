-- Monthly income, spending, and net trends per user
-- Aggregates transaction data by month for high-level financial overview
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

-- Identify internal transfer pairs (both sides):
-- An outgoing transfer has a matching incoming on same day, same absolute amount, same user, different account
INTERNAL_TRANSFER_SPENDING_IDS AS (
    SELECT DISTINCT OUTGOING.TRANSACTION_ID
    FROM TRANSACTIONS_WITH_USER AS OUTGOING
    WHERE
        OUTGOING.AMOUNT < 0  -- Outgoing
        AND EXISTS (
            SELECT 1
            FROM TRANSACTIONS_WITH_USER AS INCOMING
            WHERE
                INCOMING.USER_ID = OUTGOING.USER_ID
                AND INCOMING.ACCOUNT_ID != OUTGOING.ACCOUNT_ID
                AND INCOMING.BOOKING_DATE = OUTGOING.BOOKING_DATE
                AND INCOMING.AMOUNT = -OUTGOING.AMOUNT  -- Opposite amount
        )
),

-- Also identify the income side of internal transfers
INTERNAL_TRANSFER_INCOME_IDS AS (
    SELECT DISTINCT INCOMING.TRANSACTION_ID
    FROM TRANSACTIONS_WITH_USER AS INCOMING
    WHERE
        INCOMING.AMOUNT > 0  -- Incoming
        AND EXISTS (
            SELECT 1
            FROM TRANSACTIONS_WITH_USER AS OUTGOING
            WHERE
                OUTGOING.USER_ID = INCOMING.USER_ID
                AND OUTGOING.ACCOUNT_ID != INCOMING.ACCOUNT_ID
                AND OUTGOING.BOOKING_DATE = INCOMING.BOOKING_DATE
                AND OUTGOING.AMOUNT = -INCOMING.AMOUNT  -- Opposite amount
        )
),

-- Filter out both sides of internal transfers
FILTERED_TRANSACTIONS AS (
    SELECT *
    FROM TRANSACTIONS_WITH_USER
    WHERE
        TRANSACTION_ID NOT IN (
            SELECT SPEND.TRANSACTION_ID FROM INTERNAL_TRANSFER_SPENDING_IDS AS SPEND
        )
        AND TRANSACTION_ID NOT IN (
            SELECT INC.TRANSACTION_ID FROM INTERNAL_TRANSFER_INCOME_IDS AS INC
        )
),

MONTHLY_DATA AS (
    SELECT
        DATE_TRUNC('month', TXN.BOOKING_DATE)::DATE                   AS MONTH_START,
        TXN.USER_ID,
        TXN.CURRENCY,
        -- Income: positive amounts
        SUM(CASE WHEN TXN.AMOUNT > 0 THEN TXN.AMOUNT ELSE 0 END)      AS TOTAL_INCOME,
        -- Spending: absolute value of negative amounts
        SUM(CASE WHEN TXN.AMOUNT < 0 THEN ABS(TXN.AMOUNT) ELSE 0 END) AS TOTAL_SPENDING,
        -- Net: sum of all amounts
        SUM(TXN.AMOUNT)                                               AS NET_CHANGE,
        -- Transaction counts (excluding internal transfers)
        COUNT(*)                                                      AS TOTAL_TRANSACTIONS,
        COUNT(CASE WHEN TXN.AMOUNT > 0 THEN 1 END)                    AS INCOME_TRANSACTIONS,
        COUNT(CASE WHEN TXN.AMOUNT < 0 THEN 1 END)                    AS SPENDING_TRANSACTIONS
    FROM FILTERED_TRANSACTIONS AS TXN
    GROUP BY
        DATE_TRUNC('month', TXN.BOOKING_DATE)::DATE,
        TXN.USER_ID,
        TXN.CURRENCY
)

SELECT
    MONTH_START,
    USER_ID,
    CURRENCY,
    TOTAL_INCOME,
    TOTAL_SPENDING,
    NET_CHANGE,
    -- Savings rate: what percentage of income was saved (not spent)
    CASE
        WHEN TOTAL_INCOME > 0
            THEN ROUND((TOTAL_INCOME - TOTAL_SPENDING) / TOTAL_INCOME * 100, 2)
        ELSE 0
    END AS SAVINGS_RATE_PCT,
    TOTAL_TRANSACTIONS,
    INCOME_TRANSACTIONS,
    SPENDING_TRANSACTIONS
FROM MONTHLY_DATA
