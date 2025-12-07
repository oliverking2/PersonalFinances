select
bookings.unnest.transactionId,
'booked' as transactionType,
bookings.unnest.bookingDate,
bookings.unnest.valueDate,
bookings.unnest.bookingDateTime,
bookings.unnest.valueDateTime,
bookings.unnest.transactionAmount.amount as transactionAmount,
bookings.unnest.transactionAmount.currency as transactionAmountCurrency,
bookings.unnest.debtorAccount,
bookings.unnest.remittanceInformationUnstructured,
bookings.unnest.proprietaryBankTransactionCode,
bookings.unnest.internalTransactionId,
bookings.unnest.entryReference,
bookings.unnest.creditorName,
bookings.unnest.debtorName,
bookings.unnest.additionalInformation,
bookings.unnest.creditorAccount,
bookings.unnest.currencyExchange.instructedAmount.amount as currencyExchangeInstructedAmount,
bookings.unnest.currencyExchange.instructedAmount.currency as currencyExchangeInstructedAmountCurrency,
bookings.unnest.currencyExchange.sourceCurrency as currencyExchangeSourceCurrency,
bookings.unnest.currencyExchange.exchangeRate as currencyExchangeRate,
from
{{ ref('bronze_raw_transactions') }},
UNNEST(struct_extract(transactions,
'booked')) AS bookings

union all by name

select
bookings.unnest.transactionId,
'pending' as transactionType,
bookings.unnest.bookingDate,
bookings.unnest.bookingDateTime,
bookings.unnest.transactionAmount.amount as transactionAmount,
bookings.unnest.transactionAmount.currency as transactionAmountCurrency,
bookings.unnest.debtorAccount,
bookings.unnest.remittanceInformationUnstructured,
bookings.unnest.proprietaryBankTransactionCode,
bookings.unnest.creditorName,
bookings.unnest.debtorName,
from
{{ ref('bronze_raw_transactions') }},
UNNEST(struct_extract(transactions,
'pending')) AS bookings
