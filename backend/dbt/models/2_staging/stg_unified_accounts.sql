-- Staging model for unified accounts
-- Cleans and normalizes account data, including credit card balance normalization
--
-- Credit card balance normalization:
-- - Positive raw balance with credit limit = available credit (Nationwide style)
--   -> Convert to owed: credit_limit - available_credit
-- - Negative raw balance = amount owed (Amex style)
--   -> Keep as absolute value
-- - No credit limit = use absolute value

SELECT
    ID,
    CONNECTION_ID,
    PROVIDER_ID,
    ACCOUNT_TYPE,
    CATEGORY,
    CREDIT_LIMIT,
    DISPLAY_NAME,
    NAME,
    IBAN,
    CURRENCY,
    STATUS,
    LAST_SYNCED_AT,
    SYNCED_AT,
    -- Keep raw balance for reference
    BALANCE_AMOUNT AS RAW_BALANCE_AMOUNT,
    BALANCE_CURRENCY,
    BALANCE_TYPE,
    BALANCE_UPDATED_AT,
    TOTAL_VALUE,
    UNREALISED_PNL,
    -- Normalized balance: credit cards always show amount owed, others show raw balance
    CASE
        -- Credit card with positive balance and credit limit: available credit -> owed
        WHEN CATEGORY = 'credit_card' AND CREDIT_LIMIT IS NOT NULL AND BALANCE_AMOUNT > 0
            THEN GREATEST(0, CREDIT_LIMIT - BALANCE_AMOUNT)
        -- Credit card with negative balance: already shows owed
        WHEN CATEGORY = 'credit_card' AND BALANCE_AMOUNT <= 0
            THEN ABS(BALANCE_AMOUNT)
        -- Credit card without credit limit: use absolute value
        WHEN CATEGORY = 'credit_card'
            THEN ABS(BALANCE_AMOUNT)
        -- Non-credit cards: use raw balance
        ELSE BALANCE_AMOUNT
    END            AS NORMALIZED_BALANCE
FROM {{ ref("src_unified_accounts") }}
