// =============================================================================
// Jobs API Composable
// Convenience wrapper that re-exports job functions from useAccountsApi
// and adds analytics-specific triggers
// =============================================================================

import type { RefreshResponse } from '~/types/analytics'
import { useAuthenticatedFetch } from '~/composables/useAuthenticatedFetch'

// -----------------------------------------------------------------------------
// Composable Definition
// -----------------------------------------------------------------------------

export function useJobsApi() {
  const { authFetch } = useAuthenticatedFetch()

  // Get shared job functions from useAccountsApi (avoids duplication)
  const { fetchJob, fetchJobs, getLatestSyncJob, triggerConnectionSync } =
    useAccountsApi()

  // ---------------------------------------------------------------------------
  // Analytics-specific triggers (unique to this composable)
  // ---------------------------------------------------------------------------

  /**
   * Trigger an analytics refresh (dbt rebuild).
   * Returns a job ID that can be polled for status.
   *
   * @param redirectTo - URL to redirect to in the notification (optional)
   */
  async function triggerAnalyticsRefresh(
    redirectTo?: string,
  ): Promise<RefreshResponse> {
    const params = redirectTo
      ? `?redirect_to=${encodeURIComponent(redirectTo)}`
      : ''
    return authFetch<RefreshResponse>(`/api/analytics/refresh${params}`, {
      method: 'POST',
    })
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    // Re-exported from useAccountsApi
    fetchJob,
    fetchJobs,
    getLatestSyncJob,
    triggerConnectionSync,

    // Unique to this composable
    triggerAnalyticsRefresh,
  }
}
