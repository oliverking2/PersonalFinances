-- Loads account balances from PostgreSQL gc_balances table.

SELECT
    ID AS BALANCE_ID,
    ACCOUNT_ID,
    BALANCE_AMOUNT,
    BALANCE_CURRENCY,
    BALANCE_TYPE,
    CREDIT_LIMIT_INCLUDED,
    LAST_CHANGE_DATE
FROM {{ source('gocardless', 'gc_balances') }}
WHERE ACCOUNT_ID IS NOT NULL
