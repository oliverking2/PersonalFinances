-- Source model for unified institutions table
-- Provides a clean interface to the institutions data from PostgreSQL

SELECT
    ID,
    PROVIDER,
    NAME,
    LOGO_URL,
    COUNTRIES,
    CREATED_AT,
    UPDATED_AT
FROM {{ source('unified', 'institutions') }}
