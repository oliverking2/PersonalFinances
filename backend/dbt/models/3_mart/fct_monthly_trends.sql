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

-- Identify internal transfer pairs using a single equi-join (more efficient than correlated EXISTS)
-- An internal transfer has matching transactions: same user, different accounts, same date, opposite amounts
INTERNAL_TRANSFER_PAIRS AS (
    SELECT
        OUTGOING.TRANSACTION_ID AS OUTGOING_ID,
        INCOMING.TRANSACTION_ID AS INCOMING_ID
    FROM TRANSACTIONS_WITH_USER AS OUTGOING
    INNER JOIN TRANSACTIONS_WITH_USER AS INCOMING
        ON
            OUTGOING.USER_ID = INCOMING.USER_ID
            AND OUTGOING.ACCOUNT_ID != INCOMING.ACCOUNT_ID
            AND OUTGOING.BOOKING_DATE = INCOMING.BOOKING_DATE
            AND OUTGOING.AMOUNT = -INCOMING.AMOUNT
    WHERE OUTGOING.AMOUNT < 0  -- Outgoing has negative amount
),

-- Collect all transaction IDs that are part of internal transfers (both sides)
INTERNAL_TRANSFER_IDS AS (
    SELECT OUTGOING_ID AS TRANSACTION_ID FROM INTERNAL_TRANSFER_PAIRS
    UNION
    SELECT INCOMING_ID AS TRANSACTION_ID FROM INTERNAL_TRANSFER_PAIRS
),

-- Filter out internal transfers using anti-join pattern
FILTERED_TRANSACTIONS AS (
    SELECT TXN.*
    FROM TRANSACTIONS_WITH_USER AS TXN
    LEFT JOIN INTERNAL_TRANSFER_IDS AS ITR ON TXN.TRANSACTION_ID = ITR.TRANSACTION_ID
    WHERE ITR.TRANSACTION_ID IS NULL
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
