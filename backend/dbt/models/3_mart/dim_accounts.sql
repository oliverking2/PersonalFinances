-- Dimension table for accounts with institution context
-- Joins accounts with connections and institutions to provide full context for analytics

WITH ACCOUNTS AS (
    SELECT
        ID  AS ACCOUNT_ID,
        CONNECTION_ID,
        DISPLAY_NAME,
        NAME,
        IBAN,
        CURRENCY,
        ACCOUNT_TYPE,
        CATEGORY,
        CREDIT_LIMIT,
        STATUS,
        BALANCE_AMOUNT,
        BALANCE_CURRENCY,
        BALANCE_TYPE,
        BALANCE_UPDATED_AT,
        TOTAL_VALUE,
        UNREALISED_PNL,
        PROVIDER_ID,
        -- Normalize credit card balance to always represent amount owed
        -- Positive raw balance on credit cards = available credit (Nationwide style)
        -- Negative raw balance on credit cards = amount owed (Amex style)
        CASE
            WHEN CATEGORY = 'credit_card' AND CREDIT_LIMIT IS NOT NULL AND BALANCE_AMOUNT > 0
                THEN GREATEST(0, CREDIT_LIMIT - BALANCE_AMOUNT)  -- Available credit -> owed
            WHEN CATEGORY = 'credit_card' AND BALANCE_AMOUNT <= 0
                THEN ABS(BALANCE_AMOUNT)  -- Already shows owed
            WHEN CATEGORY = 'credit_card'
                THEN ABS(BALANCE_AMOUNT)  -- No credit limit, use absolute value
            ELSE BALANCE_AMOUNT  -- Non-credit cards: use raw balance
        END AS NORMALIZED_BALANCE
    FROM {{ ref("src_unified_accounts") }}
),

CONNECTIONS AS (
    SELECT
        ID            AS CONNECTION_ID,
        USER_ID,
        INSTITUTION_ID,
        FRIENDLY_NAME AS CONNECTION_NAME,
        PROVIDER,
        STATUS        AS CONNECTION_STATUS,
        EXPIRES_AT    AS CONNECTION_EXPIRES_AT
    FROM {{ ref("src_unified_connections") }}
),

INSTITUTIONS AS (
    SELECT
        ID       AS INSTITUTION_ID,
        NAME     AS INSTITUTION_NAME,
        LOGO_URL AS INSTITUTION_LOGO_URL
    FROM {{ ref("src_unified_institutions") }}
)

SELECT
    ACC.ACCOUNT_ID,
    CON.USER_ID,
    COALESCE(ACC.DISPLAY_NAME, ACC.NAME, 'Unknown Account') AS DISPLAY_NAME,
    ACC.CURRENCY,
    ACC.ACCOUNT_TYPE,
    ACC.CATEGORY,
    ACC.CREDIT_LIMIT,
    ACC.STATUS                                              AS ACCOUNT_STATUS,
    ACC.BALANCE_AMOUNT                                      AS RAW_BALANCE_AMOUNT,
    ACC.NORMALIZED_BALANCE                                  AS BALANCE_AMOUNT,
    ACC.BALANCE_CURRENCY,
    ACC.BALANCE_TYPE,
    ACC.BALANCE_UPDATED_AT,
    ACC.TOTAL_VALUE,
    ACC.UNREALISED_PNL,
    ACC.PROVIDER_ID,
    CON.CONNECTION_ID,
    CON.CONNECTION_NAME,
    CON.PROVIDER,
    CON.CONNECTION_STATUS,
    CON.CONNECTION_EXPIRES_AT,
    INS.INSTITUTION_ID,
    INS.INSTITUTION_NAME,
    INS.INSTITUTION_LOGO_URL
FROM ACCOUNTS AS ACC
INNER JOIN CONNECTIONS AS CON ON ACC.CONNECTION_ID = CON.CONNECTION_ID
INNER JOIN INSTITUTIONS AS INS ON CON.INSTITUTION_ID = INS.INSTITUTION_ID
