with raw_data as (
    select * from {{ ref('src_gocardless_transactions') }}
),

booked as (
    select UNNEST(STRUCT_EXTRACT(transactions, 'booked')) as txn, last_updated, _extract_dt
    from raw_data
),

pending as (
    select UNNEST(STRUCT_EXTRACT(transactions, 'pending')) as txn, last_updated, _extract_dt
    from raw_data
),

all_transactions as (
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
    txn.currencyexchange.exchangerate as currency_exchange_rate,
    last_updated, _extract_dt
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
    last_updated, _extract_dt
from
    pending
)

select
    transaction_id,
    transaction_type,
    booking_date,
    value_date,
    booking_datetime,
    value_datetime,
    transaction_amount,
    transaction_amount_currency,
    debtor_account,
    remittance_information_unstructured,
    proprietary_bank_transaction_code,
    internal_transaction_id,
    entry_reference,
    creditor_name,
    debtor_name,
    additional_information,
    creditor_account,
    currency_exchange_instructed_amount,
    currency_exchange_instructed_amount_currency,
    currency_exchange_source_currency,
    currency_exchange_rate,
last_updated, _extract_dt
from all_transactions
qualify row_number() over (partition by transaction_id order by _extract_dt desc) = 1
