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
    txn.transactionid,
    'booked' as transactiontype,
    txn.bookingdate,
    txn.valuedate,
    txn.bookingdatetime,
    txn.valuedatetime,
    txn.transactionamount.amount as transactionamount,
    txn.transactionamount.currency as transactionamountcurrency,
    txn.debtoraccount,
    txn.remittanceinformationunstructured,
    txn.proprietarybanktransactioncode,
    txn.internaltransactionid,
    txn.entryreference,
    txn.creditorname,
    txn.debtorname,
    txn.additionalinformation,
    txn.creditoraccount,
    txn.currencyexchange.instructedamount.amount as currencyexchangeinstructedamount,
    txn.currencyexchange.instructedamount.currency as currencyexchangeinstructedamountcurrency,
    txn.currencyexchange.sourcecurrency as currencyexchangesourcecurrency,
    txn.currencyexchange.exchangerate as currencyexchangerate
from
    booked

union all by name

select
    txn.transactionid,
    'pending' as transactiontype,
    txn.bookingdate,
    txn.bookingdatetime,
    txn.transactionamount.amount as transactionamount,
    txn.transactionamount.currency as transactionamountcurrency,
    txn.debtoraccount,
    txn.remittanceinformationunstructured,
    txn.proprietarybanktransactioncode,
    txn.creditorname,
    txn.debtorname
from
    pending
