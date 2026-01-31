// =============================================================================
// Planned Transactions Types
// TypeScript interfaces for planned transactions API contracts
// =============================================================================

// -----------------------------------------------------------------------------
// Enums
// -----------------------------------------------------------------------------

export type RecurringFrequency =
  | 'weekly'
  | 'fortnightly'
  | 'monthly'
  | 'quarterly'
  | 'annual'

export type TransactionDirection = 'income' | 'expense'

// -----------------------------------------------------------------------------
// Planned Transaction Model
// -----------------------------------------------------------------------------

export interface PlannedTransaction {
  id: string
  name: string
  amount: string // Decimal as string (positive = income, negative = expense)
  currency: string
  frequency: RecurringFrequency | null // null = one-time
  next_expected_date: string | null // ISO datetime
  end_date: string | null // ISO datetime (when recurring should stop)
  account_id: string | null
  account_name: string | null
  notes: string | null
  enabled: boolean
  direction: TransactionDirection
  created_at: string // ISO datetime
  updated_at: string // ISO datetime
}

// -----------------------------------------------------------------------------
// API Response Types
// -----------------------------------------------------------------------------

export interface PlannedTransactionListResponse {
  transactions: PlannedTransaction[]
  total: number
}

export interface PlannedTransactionSummary {
  total_planned: number
  income_count: number
  expense_count: number
  monthly_income: string // Decimal as string
  monthly_expenses: string
  monthly_net: string
}

// -----------------------------------------------------------------------------
// API Request Types
// -----------------------------------------------------------------------------

export interface PlannedTransactionCreateRequest {
  name: string
  amount: string | number // Decimal as string or number
  currency?: string
  frequency?: RecurringFrequency | null
  next_expected_date?: string | null
  end_date?: string | null
  account_id?: string | null
  notes?: string | null
  enabled?: boolean
}

export interface PlannedTransactionUpdateRequest {
  name?: string
  amount?: string | number
  currency?: string
  frequency?: RecurringFrequency | null
  next_expected_date?: string | null
  end_date?: string | null
  account_id?: string | null
  notes?: string | null
  enabled?: boolean
  // Clear flags for nullable fields
  clear_frequency?: boolean
  clear_end_date?: boolean
  clear_account_id?: boolean
  clear_notes?: boolean
}

// -----------------------------------------------------------------------------
// Helper Functions
// -----------------------------------------------------------------------------

export function getFrequencyLabel(
  frequency: RecurringFrequency | null,
): string {
  if (!frequency) return 'One-time'
  const labels: Record<RecurringFrequency, string> = {
    weekly: 'Weekly',
    fortnightly: 'Fortnightly',
    monthly: 'Monthly',
    quarterly: 'Quarterly',
    annual: 'Annual',
  }
  return labels[frequency] || frequency
}
