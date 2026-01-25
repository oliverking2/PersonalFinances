-- Daily balance history per account
-- Uses balance snapshots from GoCardless to track account balances over time

WITH BALANCES AS (
    SELECT
        ACCOUNT_ID AS GC_ACCOUNT_ID,  -- GoCardless bank account ID
        BALANCE_AMOUNT,
        BALANCE_TYPE,
        LAST_CHANGE_DATE
    FROM {{ ref('src_gocardless_account_balances') }}
    WHERE LAST_CHANGE_DATE IS NOT NULL
),

ACCOUNTS AS (
    SELECT
        ACCOUNT_ID,
        USER_ID,
        PROVIDER_ID,  -- This is the gc_bank_accounts.id
        DISPLAY_NAME,
        CURRENCY
    FROM {{ ref('dim_accounts') }}
),

-- Deduplicate to one balance per account per day per type
-- Keep the most recent record for each day
DAILY_BALANCES AS (
    SELECT
        BAL.GC_ACCOUNT_ID,
        BAL.BALANCE_AMOUNT,
        BAL.BALANCE_TYPE,
        BAL.LAST_CHANGE_DATE::DATE AS BALANCE_DATE,
        BAL.LAST_CHANGE_DATE       AS SNAPSHOT_AT
    FROM BALANCES AS BAL
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY BAL.GC_ACCOUNT_ID, BAL.LAST_CHANGE_DATE::DATE, BAL.BALANCE_TYPE
        ORDER BY BAL.LAST_CHANGE_DATE DESC
    ) = 1
)

SELECT
    DAILY.BALANCE_DATE,
    ACC.ACCOUNT_ID,
    ACC.USER_ID,
    ACC.DISPLAY_NAME AS ACCOUNT_NAME,
    ACC.CURRENCY,
    DAILY.BALANCE_AMOUNT,
    DAILY.BALANCE_TYPE,
    DAILY.SNAPSHOT_AT
FROM DAILY_BALANCES AS DAILY
INNER JOIN ACCOUNTS AS ACC ON DAILY.GC_ACCOUNT_ID = ACC.PROVIDER_ID
