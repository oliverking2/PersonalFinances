-- Source model for manual asset value snapshots table
-- Provides historical value data for manual assets

SELECT
    ID,
    ASSET_ID,
    VALUE,
    CURRENCY,
    NOTES,
    CAPTURED_AT
FROM {{ source('unified', 'manual_asset_value_snapshots') }}
