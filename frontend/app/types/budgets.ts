// =============================================================================
// Budget Types
// TypeScript interfaces for budgets and API contracts
// =============================================================================

// -----------------------------------------------------------------------------
// Enums (matching backend)
// -----------------------------------------------------------------------------

export type BudgetPeriod = 'monthly'

export type BudgetStatus = 'ok' | 'warning' | 'exceeded'

// -----------------------------------------------------------------------------
// Budget
// Represents a spending limit for a specific tag/category
// -----------------------------------------------------------------------------

export interface Budget {
  id: string
  tag_id: string
  tag_name: string
  tag_colour: string
  amount: number // Budget amount (positive)
  currency: string
  warning_threshold: number // Decimal (0.8 = 80%)
  enabled: boolean
  created_at: string
  updated_at: string
}

// -----------------------------------------------------------------------------
// Budget with Spending
// Budget with current period spending information
// -----------------------------------------------------------------------------

export interface BudgetWithSpending extends Budget {
  spent_amount: number // How much spent this period
  remaining_amount: number // Budget - Spent
  percentage_used: number // 0-100+
  status: BudgetStatus
}

// -----------------------------------------------------------------------------
// API Response Types
// -----------------------------------------------------------------------------

export interface BudgetListResponse {
  budgets: Budget[]
  total: number
}

export interface BudgetSummaryResponse {
  total_budgets: number
  active_budgets: number
  total_budgeted: number
  total_spent: number
  budgets_on_track: number
  budgets_warning: number
  budgets_exceeded: number
}

// -----------------------------------------------------------------------------
// API Request Types
// -----------------------------------------------------------------------------

export interface BudgetCreateRequest {
  tag_id: string
  amount: number
  currency?: string
  warning_threshold?: number
}

export interface BudgetUpdateRequest {
  amount?: number
  warning_threshold?: number
  enabled?: boolean
}

// -----------------------------------------------------------------------------
// Helper Functions
// -----------------------------------------------------------------------------

// Get status label for display
export function getStatusLabel(status: BudgetStatus): string {
  const labels: Record<BudgetStatus, string> = {
    ok: 'On Track',
    warning: 'Warning',
    exceeded: 'Exceeded',
  }
  return labels[status] || status
}

// Get status colour class
export function getStatusColour(status: BudgetStatus): string {
  const colours: Record<BudgetStatus, string> = {
    ok: 'text-emerald-400',
    warning: 'text-amber-400',
    exceeded: 'text-red-400',
  }
  return colours[status] || 'text-gray-400'
}

// Get status background colour class
export function getStatusBgColour(status: BudgetStatus): string {
  const colours: Record<BudgetStatus, string> = {
    ok: 'bg-emerald-500/20',
    warning: 'bg-amber-500/20',
    exceeded: 'bg-red-500/20',
  }
  return colours[status] || 'bg-gray-500/20'
}

// Get progress bar colour class
export function getProgressBarColour(status: BudgetStatus): string {
  const colours: Record<BudgetStatus, string> = {
    ok: 'bg-emerald-500',
    warning: 'bg-amber-500',
    exceeded: 'bg-red-500',
  }
  return colours[status] || 'bg-gray-500'
}
