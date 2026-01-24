// =============================================================================
// Transactions Types
// TypeScript interfaces for transaction data and API contracts
// =============================================================================

// -----------------------------------------------------------------------------
// Transaction
// Represents a single bank transaction
// -----------------------------------------------------------------------------

export interface Transaction {
  id: string
  account_id: string
  booking_date: string | null // ISO date (YYYY-MM-DD)
  value_date: string | null // ISO date (YYYY-MM-DD)
  amount: number // Negative for debits, positive for credits
  currency: string
  description: string | null
  merchant_name: string | null
  category: string | null // Future: user-editable
}

// -----------------------------------------------------------------------------
// API Response Types
// -----------------------------------------------------------------------------

export interface TransactionListResponse {
  transactions: Transaction[]
  total: number
  page: number
  page_size: number
}

// -----------------------------------------------------------------------------
// API Query Types
// -----------------------------------------------------------------------------

export interface TransactionQueryParams {
  account_id?: string
  start_date?: string // ISO date (YYYY-MM-DD)
  end_date?: string // ISO date (YYYY-MM-DD)
  min_amount?: number
  max_amount?: number
  search?: string
  page?: number
  page_size?: number
}

// -----------------------------------------------------------------------------
// Frontend-only Types (for UI grouping)
// -----------------------------------------------------------------------------

export interface TransactionDayGroup {
  date: string // ISO date (YYYY-MM-DD)
  dateDisplay: string // "Today", "Yesterday", "Mon 20 Jan"
  transactions: Transaction[]
  dayTotal: number // Sum of all transaction amounts for the day
}
