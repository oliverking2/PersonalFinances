// =============================================================================
// Subscription Types
// TypeScript interfaces for recurring patterns/subscriptions and API contracts
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
  | 'irregular'

export type RecurringStatus =
  | 'detected'
  | 'confirmed'
  | 'dismissed'
  | 'paused'
  | 'manual'

// -----------------------------------------------------------------------------
// Subscription (Recurring Pattern)
// Represents a detected or user-confirmed recurring payment
// -----------------------------------------------------------------------------

export interface Subscription {
  id: string
  merchant_pattern: string // Normalised merchant name
  display_name: string // User-friendly name
  expected_amount: number // Expected transaction amount (negative)
  currency: string
  frequency: RecurringFrequency
  status: RecurringStatus
  confidence_score: number // Detection confidence (0.0-1.0)
  occurrence_count: number // Number of matched transactions
  account_id: string | null
  notes: string | null
  last_occurrence_date: string | null // ISO datetime
  next_expected_date: string | null // ISO datetime
  monthly_equivalent: number // Amount converted to monthly
  created_at: string
  updated_at: string
}

// -----------------------------------------------------------------------------
// API Response Types
// -----------------------------------------------------------------------------

export interface SubscriptionListResponse {
  subscriptions: Subscription[]
  total: number
  monthly_total: number
}

export interface UpcomingBill {
  id: string
  display_name: string
  merchant_pattern: string
  expected_amount: number
  currency: string
  next_expected_date: string // ISO datetime
  frequency: RecurringFrequency
  confidence_score: number
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

export interface SubscriptionSummary {
  monthly_total: number
  total_count: number
  confirmed_count: number
  detected_count: number
  paused_count: number
}

// -----------------------------------------------------------------------------
// API Request Types
// -----------------------------------------------------------------------------

export interface SubscriptionCreateRequest {
  merchant_pattern: string
  expected_amount: number
  frequency: RecurringFrequency
  currency?: string
  account_id?: string
  display_name?: string
  notes?: string
  anchor_date?: string // ISO date (YYYY-MM-DD)
}

export interface SubscriptionUpdateRequest {
  status?: RecurringStatus
  display_name?: string
  notes?: string
  expected_amount?: number
  frequency?: RecurringFrequency
}

// -----------------------------------------------------------------------------
// Query Parameters
// -----------------------------------------------------------------------------

// Subscription transaction (simplified view of linked transactions)
export interface SubscriptionTransaction {
  id: string
  booking_date: string | null
  amount: number
  currency: string
  description: string | null
  merchant_name: string | null
}

export interface SubscriptionTransactionsResponse {
  transactions: SubscriptionTransaction[]
  total: number
}

export interface SubscriptionQueryParams {
  status?: RecurringStatus
  frequency?: RecurringFrequency
  min_confidence?: number
  include_dismissed?: boolean
}

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
    irregular: 'Irregular',
  }
  return labels[frequency] || frequency
}

// Get display label for status
export function getStatusLabel(status: RecurringStatus): string {
  const labels: Record<RecurringStatus, string> = {
    detected: 'Detected',
    confirmed: 'Confirmed',
    dismissed: 'Dismissed',
    paused: 'Paused',
    manual: 'Manual',
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
    irregular: 'Irreg',
  }
  return labels[frequency] || frequency
}
