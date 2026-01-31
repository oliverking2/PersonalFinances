-- Source model for planned transactions table
-- Provides a clean interface to planned income/expenses for forecasting

SELECT
    ID,
    USER_ID,
    NAME,
    AMOUNT,
    CURRENCY,
    FREQUENCY,
    NEXT_EXPECTED_DATE,
    END_DATE,
    ACCOUNT_ID,
    NOTES,
    ENABLED,
    CREATED_AT,
    UPDATED_AT
FROM {{ source('unified', 'planned_transactions') }}
