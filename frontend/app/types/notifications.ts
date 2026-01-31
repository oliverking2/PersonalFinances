// =============================================================================
// Notification Types
// TypeScript interfaces for in-app notifications and API contracts
// =============================================================================

// -----------------------------------------------------------------------------
// Enums (matching backend)
// -----------------------------------------------------------------------------

export type NotificationType =
  | 'budget_warning'
  | 'budget_exceeded'
  | 'export_complete'
  | 'export_failed'
  | 'sync_complete'
  | 'sync_failed'
  | 'analytics_refresh_complete'
  | 'analytics_refresh_failed'

// -----------------------------------------------------------------------------
// Metadata Types (type-specific data stored in notification.metadata)
// -----------------------------------------------------------------------------

export interface BudgetNotificationMetadata {
  budget_id: string
  tag_name: string
  period_key: string
  budget_amount: number
  spent_amount: number
  percentage: number
}

export interface ExportNotificationMetadata {
  job_id: string
  dataset_name: string
  download_url?: string
  error_message?: string
}

export interface SyncNotificationMetadata {
  job_id: string
  connection_name: string
  error_message?: string
}

export interface AnalyticsRefreshNotificationMetadata {
  job_id: string
  redirect_to: string
  error_message?: string
}

// -----------------------------------------------------------------------------
// Notification
// Represents an in-app notification
// -----------------------------------------------------------------------------

export interface Notification {
  id: string
  notification_type: NotificationType
  title: string
  message: string
  read: boolean
  metadata: Record<string, unknown>
  created_at: string // ISO datetime
  read_at: string | null // ISO datetime
}

// -----------------------------------------------------------------------------
// API Response Types
// -----------------------------------------------------------------------------

export interface NotificationListResponse {
  notifications: Notification[]
  total: number
  unread_count: number
}

export interface NotificationCountResponse {
  unread_count: number
}

// -----------------------------------------------------------------------------
// Helper Functions
// -----------------------------------------------------------------------------

// Get notification type label for display
export function getNotificationTypeLabel(
  notificationType: NotificationType,
): string {
  const labels: Record<NotificationType, string> = {
    budget_warning: 'Budget Warning',
    budget_exceeded: 'Budget Exceeded',
    export_complete: 'Export Complete',
    export_failed: 'Export Failed',
    sync_complete: 'Sync Complete',
    sync_failed: 'Sync Failed',
    analytics_refresh_complete: 'Analytics Refreshed',
    analytics_refresh_failed: 'Analytics Refresh Failed',
  }
  return labels[notificationType] || notificationType
}

// Get notification type colour class (text colour)
export function getNotificationTypeColour(
  notificationType: NotificationType,
): string {
  const colours: Record<NotificationType, string> = {
    budget_warning: 'text-amber-400',
    budget_exceeded: 'text-red-400',
    export_complete: 'text-emerald-400',
    export_failed: 'text-red-400',
    sync_complete: 'text-emerald-400',
    sync_failed: 'text-red-400',
    analytics_refresh_complete: 'text-emerald-400',
    analytics_refresh_failed: 'text-red-400',
  }
  return colours[notificationType] || 'text-gray-400'
}

// Get notification type background colour class
export function getNotificationTypeBgColour(
  notificationType: NotificationType,
): string {
  const colours: Record<NotificationType, string> = {
    budget_warning: 'bg-amber-500/20',
    budget_exceeded: 'bg-red-500/20',
    export_complete: 'bg-emerald-500/20',
    export_failed: 'bg-red-500/20',
    sync_complete: 'bg-emerald-500/20',
    sync_failed: 'bg-red-500/20',
    analytics_refresh_complete: 'bg-emerald-500/20',
    analytics_refresh_failed: 'bg-red-500/20',
  }
  return colours[notificationType] || 'bg-gray-500/20'
}

// Check if notification type is an error/warning type
export function isErrorNotification(
  notificationType: NotificationType,
): boolean {
  return [
    'budget_exceeded',
    'export_failed',
    'sync_failed',
    'analytics_refresh_failed',
  ].includes(notificationType)
}

export function isWarningNotification(
  notificationType: NotificationType,
): boolean {
  return notificationType === 'budget_warning'
}

export function isSuccessNotification(
  notificationType: NotificationType,
): boolean {
  return [
    'export_complete',
    'sync_complete',
    'analytics_refresh_complete',
  ].includes(notificationType)
}

// Format relative time for notification display
export function formatNotificationTime(createdAt: string): string {
  const date = new Date(createdAt)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`

  // For older notifications, show the date
  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
  })
}
