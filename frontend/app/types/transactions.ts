// =============================================================================
// Transactions Types
// TypeScript interfaces for transaction data and API contracts
// =============================================================================

// -----------------------------------------------------------------------------
// Transaction
// Represents a single bank transaction
// -----------------------------------------------------------------------------

import type { RecurringFrequency, RecurringStatus } from './subscriptions'
export interface TransactionTag {
  id: string
  name: string
  colour: string | null
  is_auto: boolean // True if tag was applied by an auto-tagging rule
  rule_id: string | null // ID of the rule that applied this tag (if auto)
  rule_name: string | null // Name of the rule that applied this tag (if auto)
}

export interface TransactionSplit {
  id: string
  tag_id: string
  tag_name: string
  tag_colour: string | null
  amount: number // Always positive
  is_auto: boolean // True if split was created by an auto-tagging rule
  rule_id: string | null // ID of the rule that created this split (if auto)
  rule_name: string | null // Name of the rule that created this split (if auto)
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
  user_note: string | null // User-added note
  tags: TransactionTag[] // User-defined tags
  splits: TransactionSplit[] // Transaction splits for budgeting
  // Recurring pattern info (from detection)
  recurring_pattern_id: string | null
  recurring_frequency: RecurringFrequency | null
  recurring_status: RecurringStatus | null
}

// Re-export recurring types from subscriptions (single source of truth)
export type { RecurringFrequency, RecurringStatus } from './subscriptions'

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

// -----------------------------------------------------------------------------
// Split Request/Response Types
// -----------------------------------------------------------------------------

export interface SplitRequest {
  tag_id: string
  amount: number // Must be positive
}

export interface SetSplitsRequest {
  splits: SplitRequest[]
}

export interface TransactionSplitsResponse {
  transaction_id: string
  splits: TransactionSplit[]
}

export interface UpdateNoteRequest {
  user_note: string | null
}
