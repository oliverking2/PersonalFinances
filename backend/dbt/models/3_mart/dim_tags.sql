-- Dimension table for user-defined tags
-- Provides tag metadata for analytics joins

SELECT
    ID AS TAG_ID,
    USER_ID,
    NAME,
    COLOUR,
    CREATED_AT
FROM {{ ref("src_unified_tags") }}
