// =============================================================================
// Alerts API Composable
// All API functions for managing spending alerts
// =============================================================================

import type {
  Alert,
  AlertListResponse,
  AlertCountResponse,
} from '~/types/alerts'
import {
  useAuthenticatedFetch,
  ApiError,
} from '~/composables/useAuthenticatedFetch'

// -----------------------------------------------------------------------------
// Composable Definition
// -----------------------------------------------------------------------------

export function useAlertsApi() {
  const { authFetch } = useAuthenticatedFetch()

  // ---------------------------------------------------------------------------
  // Alerts Read
  // ---------------------------------------------------------------------------

  // Fetch all alerts for the current user
  async function fetchAlerts(): Promise<AlertListResponse> {
    return authFetch<AlertListResponse>('/api/alerts')
  }

  // Get a single alert by ID
  async function fetchAlert(alertId: string): Promise<Alert> {
    return authFetch<Alert>(`/api/alerts/${alertId}`)
  }

  // Get count of pending alerts (for badge display)
  async function fetchAlertCount(): Promise<AlertCountResponse> {
    return authFetch<AlertCountResponse>('/api/alerts/count')
  }

  // ---------------------------------------------------------------------------
  // Alert Actions
  // ---------------------------------------------------------------------------

  // Acknowledge a single alert
  async function acknowledgeAlert(alertId: string): Promise<Alert> {
    return authFetch<Alert>(`/api/alerts/${alertId}/acknowledge`, {
      method: 'PUT',
    })
  }

  // Acknowledge all pending alerts
  async function acknowledgeAllAlerts(): Promise<AlertCountResponse> {
    return authFetch<AlertCountResponse>('/api/alerts/acknowledge-all', {
      method: 'PUT',
    })
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    // Read
    fetchAlerts,
    fetchAlert,
    fetchAlertCount,

    // Actions
    acknowledgeAlert,
    acknowledgeAllAlerts,

    // Export ApiError for error type checking
    ApiError,
  }
}
