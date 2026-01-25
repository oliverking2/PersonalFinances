-- Loads account details from PostgreSQL gc_bank_accounts table.

SELECT
    ID AS ACCOUNT_ID,
    BBAN,
    BIC,
    CASH_ACCOUNT_TYPE,
    CURRENCY,
    DETAILS,
    DISPLAY_NAME,
    IBAN,
    LINKED_ACCOUNTS,
    MSISDN,
    NAME,
    OWNER_ADDRESS_UNSTRUCTURED,
    OWNER_NAME,
    PRODUCT,
    STATUS,
    SCAN,
    USAGE,
    REQUISITION_ID,
    DG_TRANSACTION_EXTRACT_DATE
FROM {{ source('gocardless', 'gc_bank_accounts') }}
WHERE ID IS NOT NULL
