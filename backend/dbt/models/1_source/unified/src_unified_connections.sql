-- Source model for unified connections table
-- Provides a clean interface to the connections data from PostgreSQL

SELECT
    ID,
    USER_ID,
    PROVIDER,
    PROVIDER_ID,
    INSTITUTION_ID,
    FRIENDLY_NAME,
    STATUS,
    CREATED_AT,
    EXPIRES_AT,
    SYNCED_AT
FROM {{ source('unified', 'connections') }}
