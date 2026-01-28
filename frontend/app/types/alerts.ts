// =============================================================================
// Alert Types
// TypeScript interfaces for spending alerts and API contracts
// =============================================================================

// -----------------------------------------------------------------------------
// Enums (matching backend)
// -----------------------------------------------------------------------------

export type AlertType = 'budget_warning' | 'budget_exceeded'

export type AlertStatus = 'pending' | 'acknowledged'

// -----------------------------------------------------------------------------
// Alert
// Represents a spending alert notification
// -----------------------------------------------------------------------------

export interface Alert {
  id: string
  budget_id: string
  alert_type: AlertType
  status: AlertStatus
  period_key: string // YYYY-MM format
  budget_amount: number
  spent_amount: number
  tag_name: string | null
  acknowledged_at: string | null // ISO datetime
  created_at: string
}

// -----------------------------------------------------------------------------
// API Response Types
// -----------------------------------------------------------------------------

export interface AlertListResponse {
  alerts: Alert[]
  total: number
  pending_count: number
}

export interface AlertCountResponse {
  pending_count: number
}

// -----------------------------------------------------------------------------
// Helper Functions
// -----------------------------------------------------------------------------

// Get alert type label for display
export function getAlertTypeLabel(alertType: AlertType): string {
  const labels: Record<AlertType, string> = {
    budget_warning: 'Budget Warning',
    budget_exceeded: 'Budget Exceeded',
  }
  return labels[alertType] || alertType
}

// Get alert type colour class
export function getAlertTypeColour(alertType: AlertType): string {
  const colours: Record<AlertType, string> = {
    budget_warning: 'text-amber-400',
    budget_exceeded: 'text-red-400',
  }
  return colours[alertType] || 'text-gray-400'
}

// Get alert type background colour class
export function getAlertTypeBgColour(alertType: AlertType): string {
  const colours: Record<AlertType, string> = {
    budget_warning: 'bg-amber-500/20',
    budget_exceeded: 'bg-red-500/20',
  }
  return colours[alertType] || 'bg-gray-500/20'
}

// Get alert icon (for SVG or icon component)
export function getAlertIcon(alertType: AlertType): string {
  const icons: Record<AlertType, string> = {
    budget_warning: 'exclamation-triangle',
    budget_exceeded: 'exclamation-circle',
  }
  return icons[alertType] || 'bell'
}

// Format alert message
export function formatAlertMessage(alert: Alert): string {
  const percentage = Math.round(
    (alert.spent_amount / alert.budget_amount) * 100,
  )
  const tagName = alert.tag_name || 'Unknown category'

  if (alert.alert_type === 'budget_exceeded') {
    return `${tagName} budget exceeded (${percentage}% spent)`
  }
  return `${tagName} budget at ${percentage}%`
}
