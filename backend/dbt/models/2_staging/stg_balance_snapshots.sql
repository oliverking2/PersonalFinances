-- Staging model for balance snapshots
-- Normalizes credit card balances and negates them to represent liabilities
--
-- Credit card balance normalization (same logic as stg_unified_accounts):
-- - Positive raw balance with credit limit = available credit (Nationwide style)
--   -> Convert to owed, then negate (liability)
-- - Negative raw balance = amount owed (Amex style)
--   -> Use absolute value, then negate (liability)
-- - No credit limit = use absolute value, then negate (liability)

WITH SNAPSHOTS AS (
    SELECT
        ID,
        ACCOUNT_ID,
        BALANCE_AMOUNT,
        BALANCE_CURRENCY,
        BALANCE_TYPE,
        TOTAL_VALUE,
        UNREALISED_PNL,
        SOURCE_UPDATED_AT,
        CAPTURED_AT
    FROM {{ ref("src_balance_snapshots") }}
),

ACCOUNTS AS (
    SELECT
        ID AS ACCOUNT_ID,
        CATEGORY,
        CREDIT_LIMIT
    FROM {{ ref("src_unified_accounts") }}
)

SELECT
    SNP.ID,
    SNP.ACCOUNT_ID,
    -- Keep raw balance for reference
    SNP.BALANCE_AMOUNT AS RAW_BALANCE_AMOUNT,
    -- Normalized balance: credit cards negated as liabilities, others unchanged
    CASE
        -- Credit card with positive balance and credit limit: available credit -> owed, negated
        WHEN ACC.CATEGORY = 'credit_card' AND ACC.CREDIT_LIMIT IS NOT NULL AND SNP.BALANCE_AMOUNT > 0
            THEN -GREATEST(0, ACC.CREDIT_LIMIT - SNP.BALANCE_AMOUNT)
        -- Credit card with negative balance: already shows owed, negate absolute value
        WHEN ACC.CATEGORY = 'credit_card' AND SNP.BALANCE_AMOUNT <= 0
            THEN -ABS(SNP.BALANCE_AMOUNT)
        -- Credit card without credit limit: use absolute value, negated
        WHEN ACC.CATEGORY = 'credit_card'
            THEN -ABS(SNP.BALANCE_AMOUNT)
        -- Non-credit cards: use raw balance
        ELSE SNP.BALANCE_AMOUNT
    END                AS BALANCE_AMOUNT,
    SNP.BALANCE_CURRENCY,
    SNP.BALANCE_TYPE,
    SNP.TOTAL_VALUE,
    SNP.UNREALISED_PNL,
    SNP.SOURCE_UPDATED_AT,
    SNP.CAPTURED_AT
FROM SNAPSHOTS AS SNP
LEFT JOIN ACCOUNTS AS ACC ON SNP.ACCOUNT_ID = ACC.ACCOUNT_ID
