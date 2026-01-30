// =============================================================================
// Notifications API Composable
// All API functions for managing in-app notifications
// =============================================================================

import type {
  Notification,
  NotificationListResponse,
  NotificationCountResponse,
} from '~/types/notifications'
import {
  useAuthenticatedFetch,
  ApiError,
} from '~/composables/useAuthenticatedFetch'

// -----------------------------------------------------------------------------
// Composable Definition
// -----------------------------------------------------------------------------

export function useNotificationsApi() {
  const { authFetch } = useAuthenticatedFetch()

  // ---------------------------------------------------------------------------
  // Notifications Read
  // ---------------------------------------------------------------------------

  // Fetch notifications for the current user
  async function fetchNotifications(options?: {
    unread_only?: boolean
    limit?: number
    offset?: number
  }): Promise<NotificationListResponse> {
    const params = new URLSearchParams()
    if (options?.unread_only) params.set('unread_only', 'true')
    if (options?.limit) params.set('limit', options.limit.toString())
    if (options?.offset) params.set('offset', options.offset.toString())

    const queryString = params.toString()
    const url = queryString
      ? `/api/notifications?${queryString}`
      : '/api/notifications'

    return authFetch<NotificationListResponse>(url)
  }

  // Get count of unread notifications (for badge display)
  async function fetchUnreadCount(): Promise<NotificationCountResponse> {
    return authFetch<NotificationCountResponse>('/api/notifications/count')
  }

  // ---------------------------------------------------------------------------
  // Notification Actions
  // ---------------------------------------------------------------------------

  // Mark a single notification as read
  async function markAsRead(notificationId: string): Promise<Notification> {
    return authFetch<Notification>(
      `/api/notifications/${notificationId}/read`,
      {
        method: 'PUT',
      },
    )
  }

  // Mark all notifications as read
  async function markAllAsRead(): Promise<NotificationCountResponse> {
    return authFetch<NotificationCountResponse>('/api/notifications/read-all', {
      method: 'PUT',
    })
  }

  // Delete a notification
  async function deleteNotification(notificationId: string): Promise<void> {
    await authFetch(`/api/notifications/${notificationId}`, {
      method: 'DELETE',
    })
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    // Read
    fetchNotifications,
    fetchUnreadCount,

    // Actions
    markAsRead,
    markAllAsRead,
    deleteNotification,

    // Export ApiError for error type checking
    ApiError,
  }
}
