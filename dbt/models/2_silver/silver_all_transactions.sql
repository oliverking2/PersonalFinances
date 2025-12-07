with raw_data as (
    select * from {{ ref('bronze_raw_transactions') }}
),

booked as (
    select UNNEST(STRUCT_EXTRACT(transactions, 'booked')) as txn
    from raw_data
),

pending as (
    select UNNEST(STRUCT_EXTRACT(transactions, 'pending')) as txn
    from raw_data
)

select  -- noqa: AM07
    txn.transactionid as transaction_id,
    'booked' as transaction_type,
    txn.bookingdate as booking_date,
    txn.valuedate as value_date,
    txn.bookingdatetime as booking_datetime,
    txn.valuedatetime as value_datetime,
    txn.transactionamount.amount as transaction_amount,
    txn.transactionamount.currency as transaction_amount_currency,
    txn.debtoraccount as debtor_account,
    txn.remittanceinformationunstructured as remittance_information_unstructured,
    txn.proprietarybanktransactioncode as proprietary_bank_transaction_code,
    txn.internaltransactionid as internal_transaction_id,
    txn.entryreference as entry_reference,
    txn.creditorname as creditor_name,
    txn.debtorname as debtor_name,
    txn.additionalinformation as additional_information,
    txn.creditoraccount as creditor_account,
    txn.currencyexchange.instructedamount.amount as currency_exchange_instructed_amount,
    txn.currencyexchange.instructedamount.currency as currency_exchange_instructed_amount_currency,
    txn.currencyexchange.sourcecurrency as currency_exchange_source_currency,
    txn.currencyexchange.exchangerate as currency_exchange_rate
from
    booked

union all by name

select
    txn.transactionid as transaction_id,
    'pending' as transaction_type,
    txn.bookingdate as booking_date,
    txn.bookingdatetime as booking_datetime,
    txn.transactionamount.amount as transaction_amount,
    txn.transactionamount.currency as transaction_amount_currency,
    txn.debtoraccount as debtor_account,
    txn.remittanceinformationunstructured as remittance_information_unstructured,
    txn.proprietarybanktransactioncode as proprietary_bank_transaction_code,
    txn.creditorname as creditor_name,
    txn.debtorname as debtor_name,
from
    pending
