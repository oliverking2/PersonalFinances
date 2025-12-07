-- depends_on: {{ source('dagster','gocardless_raw_account_balances') }}

SELECT
    account_id,
    balances,
    _extract_dt
FROM
    READ_JSON(
        's3://oking-personal-finances/extracts/gocardless/*/balances/**/*.json',
        auto_detect = true,
        union_by_name = true
    )
WHERE account_id is not null