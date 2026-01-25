// =============================================================================
// Transactions Types
// TypeScript interfaces for transaction data and API contracts
// =============================================================================

// -----------------------------------------------------------------------------
// Transaction
// Represents a single bank transaction
// -----------------------------------------------------------------------------

export interface TransactionTag {
  id: string
  name: string
  colour: string | null
}

export interface Transaction {
  id: string
  account_id: string
  booking_date: string | null // ISO date (YYYY-MM-DD)
  value_date: string | null // ISO date (YYYY-MM-DD)
  amount: number // Negative for debits, positive for credits
  currency: string
  description: string | null
  merchant_name: string | null
  category: string | null // Provider category (read-only)
  tags: TransactionTag[] // User-defined tags
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
  account_ids?: string[] // Filter by accounts (transactions in ANY of these accounts)
  tag_ids?: string[] // Filter by tags (transactions matching ANY of these tags)
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
