-- Monthly income, spending, and net trends per user
-- Aggregates transaction data by month for high-level financial overview

WITH TRANSACTIONS AS (
    SELECT
        ID AS TRANSACTION_ID,
        ACCOUNT_ID,
        BOOKING_DATE,
        AMOUNT,
        CURRENCY
    FROM {{ ref('src_transactions') }}
    WHERE BOOKING_DATE IS NOT NULL
),

ACCOUNTS AS (
    SELECT
        ACCOUNT_ID,
        USER_ID
    FROM {{ ref('dim_accounts') }}
),

MONTHLY_DATA AS (
    SELECT
        DATE_TRUNC('month', TXN.BOOKING_DATE)::DATE                   AS MONTH_START,
        ACC.USER_ID,
        TXN.CURRENCY,
        -- Income: positive amounts
        SUM(CASE WHEN TXN.AMOUNT > 0 THEN TXN.AMOUNT ELSE 0 END)      AS TOTAL_INCOME,
        -- Spending: absolute value of negative amounts
        SUM(CASE WHEN TXN.AMOUNT < 0 THEN ABS(TXN.AMOUNT) ELSE 0 END) AS TOTAL_SPENDING,
        -- Net: sum of all amounts
        SUM(TXN.AMOUNT)                                               AS NET_CHANGE,
        -- Transaction counts
        COUNT(*)                                                      AS TOTAL_TRANSACTIONS,
        COUNT(CASE WHEN TXN.AMOUNT > 0 THEN 1 END)                    AS INCOME_TRANSACTIONS,
        COUNT(CASE WHEN TXN.AMOUNT < 0 THEN 1 END)                    AS SPENDING_TRANSACTIONS
    FROM TRANSACTIONS AS TXN
    INNER JOIN ACCOUNTS AS ACC ON TXN.ACCOUNT_ID = ACC.ACCOUNT_ID
    GROUP BY
        DATE_TRUNC('month', TXN.BOOKING_DATE)::DATE,
        ACC.USER_ID,
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
