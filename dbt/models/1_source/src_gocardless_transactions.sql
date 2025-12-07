-- depends_on: {{ source('dagster','gocardless_raw_transactions') }}

SELECT
    account_id,
    transactions,
    last_updated,
    _extract_dt
FROM
    READ_JSON(
        's3://oking-personal-finances/extracts/gocardless/*/transactions/**/*.json',
        auto_detect = true,
        union_by_name = true
    )
WHERE account_id is not null