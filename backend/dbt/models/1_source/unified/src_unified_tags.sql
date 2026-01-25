-- Source model for unified tags table
-- Provides a clean interface to the tags data from PostgreSQL

SELECT
    ID,
    USER_ID,
    NAME,
    COLOUR,
    CREATED_AT,
    UPDATED_AT
FROM {{ source('unified', 'tags') }}
