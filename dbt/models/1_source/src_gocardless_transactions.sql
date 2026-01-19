-- depends_on: {{ source('dagster','gocardless_raw_transactions') }}
-- Extracts raw transaction data from JSON files in S3.
-- The _extract_dt field is added by the Dagster extraction asset.

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
WHERE account_id IS NOT NULL