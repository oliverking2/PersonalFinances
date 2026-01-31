// =============================================================================
// Recurring Patterns Types
// TypeScript interfaces for recurring patterns and API contracts
// =============================================================================

// -----------------------------------------------------------------------------
// Enums (matching backend)
// -----------------------------------------------------------------------------

export type RecurringFrequency =
  | 'weekly'
  | 'fortnightly'
  | 'monthly'
  | 'quarterly'
  | 'annual'

export type RecurringStatus = 'pending' | 'active' | 'paused' | 'cancelled'

export type RecurringSource = 'detected' | 'manual'

export type RecurringDirection = 'expense' | 'income'

// -----------------------------------------------------------------------------
// Recurring Pattern
// Represents a detected or user-confirmed recurring payment
// -----------------------------------------------------------------------------

export interface RecurringPattern {
  id: string
  name: string // User-friendly name
  notes: string | null
  expected_amount: number // Expected transaction amount (always positive)
  currency: string
  frequency: RecurringFrequency
  direction: RecurringDirection // expense or income
  status: RecurringStatus
  source: RecurringSource // detected or manual
  account_id: string | null

  // Matching rules
  merchant_contains: string | null // Case-insensitive partial match
  amount_tolerance_pct: number // Default 10.0

  // Timing
  anchor_date: string | null // ISO datetime
  next_expected_date: string | null // ISO datetime
  last_matched_date: string | null // ISO datetime
  end_date: string | null // ISO datetime

  // Statistics
  match_count: number // Number of linked transactions
  confidence_score: number | null // Detection confidence (0.0-1.0)
  occurrence_count: number | null // Number of occurrences at detection

  // Detection metadata
  detection_reason: string | null

  // Computed fields from API
  monthly_equivalent: number // Amount converted to monthly

  created_at: string
  updated_at: string
}

// Legacy alias for backward compatibility during migration
export type Subscription = RecurringPattern

// -----------------------------------------------------------------------------
// API Response Types
// -----------------------------------------------------------------------------

export interface RecurringPatternListResponse {
  patterns: RecurringPattern[]
  total: number
  monthly_total: number
}

// Legacy alias
export type SubscriptionListResponse = RecurringPatternListResponse

export interface UpcomingBill {
  id: string
  name: string
  merchant_contains: string | null
  expected_amount: number
  currency: string
  next_expected_date: string // ISO datetime
  frequency: RecurringFrequency
  direction: RecurringDirection
  confidence_score: number | null
  status: RecurringStatus
  days_until: number
}

export interface UpcomingBillsResponse {
  upcoming: UpcomingBill[]
  total_expected: number
  date_range: {
    start: string // ISO date
    end: string // ISO date
  }
}

export interface RecurringSummary {
  monthly_total: number // Net (income - expenses)
  monthly_expenses: number // Total recurring expenses
  monthly_income: number // Total recurring income
  total_count: number
  expense_count: number
  income_count: number
  active_count: number
  pending_count: number
  paused_count: number
}

// Legacy alias
export type SubscriptionSummary = RecurringSummary

// -----------------------------------------------------------------------------
// API Request Types
// -----------------------------------------------------------------------------

export interface RecurringPatternCreateRequest {
  name: string
  expected_amount: number
  frequency: RecurringFrequency
  direction: RecurringDirection
  currency?: string
  account_id?: string
  notes?: string
  merchant_contains?: string
  amount_tolerance_pct?: number
  anchor_date?: string // ISO date (YYYY-MM-DD)
}

// Legacy alias
export type SubscriptionCreateRequest = RecurringPatternCreateRequest

export interface RecurringPatternUpdateRequest {
  name?: string
  notes?: string
  expected_amount?: number
  frequency?: RecurringFrequency
  merchant_contains?: string
  amount_tolerance_pct?: number
  next_expected_date?: string
}

// Legacy alias
export type SubscriptionUpdateRequest = RecurringPatternUpdateRequest

export interface CreateFromTransactionsRequest {
  transaction_ids: string[]
  name?: string
  expected_amount?: number
  frequency?: RecurringFrequency
  merchant_contains?: string
}

// -----------------------------------------------------------------------------
// Query Parameters
// -----------------------------------------------------------------------------

export interface RecurringPatternQueryParams {
  status?: RecurringStatus
  frequency?: RecurringFrequency
  direction?: RecurringDirection
  min_confidence?: number
}

// Legacy alias
export type SubscriptionQueryParams = RecurringPatternQueryParams

// Linked transaction (simplified view)
export interface PatternTransaction {
  id: string
  booking_date: string | null
  amount: number
  currency: string
  description: string | null
  merchant_name: string | null
  matched_at: string
  is_manual: boolean
}

// Legacy alias
export type SubscriptionTransaction = PatternTransaction

export interface PatternTransactionsResponse {
  transactions: PatternTransaction[]
  total: number
}

// Legacy alias
export type SubscriptionTransactionsResponse = PatternTransactionsResponse

// -----------------------------------------------------------------------------
// Helper Functions
// -----------------------------------------------------------------------------

// Get display label for frequency
export function getFrequencyLabel(frequency: RecurringFrequency): string {
  const labels: Record<RecurringFrequency, string> = {
    weekly: 'Weekly',
    fortnightly: 'Fortnightly',
    monthly: 'Monthly',
    quarterly: 'Quarterly',
    annual: 'Annual',
  }
  return labels[frequency] || frequency
}

// Get display label for status
export function getStatusLabel(status: RecurringStatus): string {
  const labels: Record<RecurringStatus, string> = {
    pending: 'Pending',
    active: 'Active',
    paused: 'Paused',
    cancelled: 'Cancelled',
  }
  return labels[status] || status
}

// Get short frequency label for badges
export function getFrequencyShortLabel(frequency: RecurringFrequency): string {
  const labels: Record<RecurringFrequency, string> = {
    weekly: 'Wkly',
    fortnightly: '2-Wkly',
    monthly: 'Mthly',
    quarterly: 'Qtrly',
    annual: 'Yrly',
  }
  return labels[frequency] || frequency
}

// Get display label for direction
export function getDirectionLabel(direction: RecurringDirection): string {
  const labels: Record<RecurringDirection, string> = {
    expense: 'Expense',
    income: 'Income',
  }
  return labels[direction] || direction
}

// Get display label for source
export function getSourceLabel(source: RecurringSource): string {
  const labels: Record<RecurringSource, string> = {
    detected: 'Detected',
    manual: 'Manual',
  }
  return labels[source] || source
}
