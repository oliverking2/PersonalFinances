-- depends_on: {{ source('dagster','gocardless_raw_account_balances') }}
-- Loads account balances from PostgreSQL gc_balances table.

SELECT
    id AS balance_id,
    account_id,
    balance_amount,
    balance_currency,
    balance_type,
    credit_limit_included,
    last_change_date
FROM pg.gc_balances
WHERE account_id IS NOT NULL
