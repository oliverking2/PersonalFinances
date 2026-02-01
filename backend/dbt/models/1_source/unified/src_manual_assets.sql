-- Source model for manual assets table
-- Provides manually tracked assets and liabilities (property, vehicles, loans, pensions)

SELECT
    ID,
    USER_ID,
    ASSET_TYPE,
    CUSTOM_TYPE,
    IS_LIABILITY,
    NAME,
    NOTES,
    CURRENT_VALUE,
    CURRENCY,
    INTEREST_RATE,
    ACQUISITION_DATE,
    ACQUISITION_VALUE,
    IS_ACTIVE,
    VALUE_UPDATED_AT,
    CREATED_AT,
    UPDATED_AT
FROM {{ source('unified', 'manual_assets') }}
WHERE IS_ACTIVE = TRUE
