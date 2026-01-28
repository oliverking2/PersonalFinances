// =============================================================================
// Savings Goal Types
// TypeScript interfaces for savings goals and API contracts
// =============================================================================

// -----------------------------------------------------------------------------
// Enums (matching backend)
// -----------------------------------------------------------------------------

export type GoalStatus = 'active' | 'paused' | 'completed' | 'cancelled'

// Tracking mode determines how goal progress is calculated
export type GoalTrackingMode = 'manual' | 'balance' | 'delta' | 'target_balance'

// -----------------------------------------------------------------------------
// Goal
// Represents a savings target the user is working towards
// -----------------------------------------------------------------------------

export interface Goal {
  id: string
  name: string
  target_amount: number // Target savings amount
  current_amount: number // Current saved amount (calculated dynamically for non-manual modes)
  currency: string
  deadline: string | null // ISO datetime
  account_id: string | null // Optional linked account
  account_name: string | null // Display name of linked account
  tracking_mode: GoalTrackingMode // How progress is tracked
  starting_balance: number | null // Account balance at goal creation (delta mode)
  target_balance: number | null // Target account balance (target_balance mode)
  status: GoalStatus
  notes: string | null
  progress_percentage: number // 0-100+
  days_remaining: number | null // Days until deadline
  created_at: string
  updated_at: string
}

// -----------------------------------------------------------------------------
// API Response Types
// -----------------------------------------------------------------------------

export interface GoalListResponse {
  goals: Goal[]
  total: number
}

export interface GoalSummaryResponse {
  total_goals: number
  active_goals: number
  completed_goals: number
  total_target: number
  total_saved: number
  overall_progress: number
}

// -----------------------------------------------------------------------------
// API Request Types
// -----------------------------------------------------------------------------

export interface GoalCreateRequest {
  name: string
  target_amount: number
  current_amount?: number // Only used for manual mode
  currency?: string
  deadline?: string // YYYY-MM-DD
  account_id?: string
  tracking_mode?: GoalTrackingMode // Default: 'manual'
  target_balance?: number // Required for target_balance mode
  notes?: string
}

export interface GoalUpdateRequest {
  name?: string
  target_amount?: number
  current_amount?: number
  deadline?: string // YYYY-MM-DD
  account_id?: string
  notes?: string
  clear_deadline?: boolean
  clear_account?: boolean
  clear_notes?: boolean
}

export interface GoalContributeRequest {
  amount: number
}

// -----------------------------------------------------------------------------
// Helper Functions
// -----------------------------------------------------------------------------

// Get status label for display
export function getStatusLabel(status: GoalStatus): string {
  const labels: Record<GoalStatus, string> = {
    active: 'Active',
    paused: 'Paused',
    completed: 'Completed',
    cancelled: 'Cancelled',
  }
  return labels[status] || status
}

// Get status colour class
export function getStatusColour(status: GoalStatus): string {
  const colours: Record<GoalStatus, string> = {
    active: 'text-emerald-400',
    paused: 'text-amber-400',
    completed: 'text-sky-400',
    cancelled: 'text-gray-400',
  }
  return colours[status] || 'text-gray-400'
}

// Get status background colour class
export function getStatusBgColour(status: GoalStatus): string {
  const colours: Record<GoalStatus, string> = {
    active: 'bg-emerald-500/20',
    paused: 'bg-amber-500/20',
    completed: 'bg-sky-500/20',
    cancelled: 'bg-gray-500/20',
  }
  return colours[status] || 'bg-gray-500/20'
}

// Get progress ring colour class (for SVG stroke)
export function getProgressColour(percentage: number): string {
  if (percentage >= 100) return 'stroke-sky-400'
  if (percentage >= 75) return 'stroke-emerald-400'
  if (percentage >= 50) return 'stroke-lime-400'
  if (percentage >= 25) return 'stroke-amber-400'
  return 'stroke-gray-500'
}

// Format days remaining as human-readable string
export function formatDaysRemaining(days: number | null): string {
  if (days === null) return 'No deadline'
  if (days < 0) return 'Overdue'
  if (days === 0) return 'Due today'
  if (days === 1) return '1 day left'
  if (days < 7) return `${days} days left`
  if (days < 30) {
    const weeks = Math.floor(days / 7)
    return weeks === 1 ? '1 week left' : `${weeks} weeks left`
  }
  const months = Math.floor(days / 30)
  return months === 1 ? '1 month left' : `${months} months left`
}

// -----------------------------------------------------------------------------
// Tracking Mode Helpers
// -----------------------------------------------------------------------------

// Get tracking mode label for display
export function getTrackingModeLabel(mode: GoalTrackingMode): string {
  const labels: Record<GoalTrackingMode, string> = {
    manual: 'Manual',
    balance: 'Account Balance',
    delta: 'Savings Progress',
    target_balance: 'Target Balance',
  }
  return labels[mode] || mode
}

// Get tracking mode description for tooltips/help text
export function getTrackingModeDescription(mode: GoalTrackingMode): string {
  const descriptions: Record<GoalTrackingMode, string> = {
    manual: 'Track contributions manually',
    balance: 'Mirror linked account balance directly',
    delta:
      'Track savings since goal creation (current balance - starting balance)',
    target_balance: 'Track progress towards a target account balance',
  }
  return descriptions[mode] || ''
}

// Check if a tracking mode allows manual contributions
export function allowsContributions(mode: GoalTrackingMode): boolean {
  return mode === 'manual'
}

// Check if a tracking mode requires an account
export function requiresAccount(mode: GoalTrackingMode): boolean {
  return mode !== 'manual'
}
