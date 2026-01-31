// =============================================================================
// Recurring Patterns API Composable
// All API functions for managing recurring patterns
// =============================================================================

import type {
  RecurringPattern,
  RecurringPatternListResponse,
  RecurringPatternCreateRequest,
  RecurringPatternUpdateRequest,
  RecurringPatternQueryParams,
  UpcomingBillsResponse,
  RecurringSummary,
  PatternTransactionsResponse,
  CreateFromTransactionsRequest,
} from '~/types/recurring'
import {
  useAuthenticatedFetch,
  ApiError,
} from '~/composables/useAuthenticatedFetch'

// -----------------------------------------------------------------------------
// Composable Definition
// -----------------------------------------------------------------------------

export function useRecurringApi() {
  const { authFetch } = useAuthenticatedFetch()

  // ---------------------------------------------------------------------------
  // Patterns CRUD
  // ---------------------------------------------------------------------------

  // Fetch all patterns with optional filters
  async function fetchPatterns(
    params?: RecurringPatternQueryParams,
  ): Promise<RecurringPatternListResponse> {
    // Build query string from params
    const query = new URLSearchParams()
    if (params?.status) query.set('status', params.status)
    if (params?.frequency) query.set('frequency', params.frequency)
    if (params?.direction) query.set('direction', params.direction)
    if (params?.min_confidence !== undefined)
      query.set('min_confidence', String(params.min_confidence))

    const queryStr = query.toString()
    const url = queryStr
      ? `/api/recurring/patterns?${queryStr}`
      : '/api/recurring/patterns'

    return authFetch<RecurringPatternListResponse>(url)
  }

  // Create a new pattern manually
  async function createPattern(
    req: RecurringPatternCreateRequest,
  ): Promise<RecurringPattern> {
    return authFetch<RecurringPattern>('/api/recurring/patterns', {
      method: 'POST',
      body: req,
    })
  }

  // Get a single pattern by ID
  async function fetchPattern(patternId: string): Promise<RecurringPattern> {
    return authFetch<RecurringPattern>(`/api/recurring/patterns/${patternId}`)
  }

  // Get transactions linked to a pattern
  async function fetchPatternTransactions(
    patternId: string,
  ): Promise<PatternTransactionsResponse> {
    return authFetch<PatternTransactionsResponse>(
      `/api/recurring/patterns/${patternId}/transactions`,
    )
  }

  // Update a pattern's details
  async function updatePattern(
    patternId: string,
    req: RecurringPatternUpdateRequest,
  ): Promise<RecurringPattern> {
    return authFetch<RecurringPattern>(`/api/recurring/patterns/${patternId}`, {
      method: 'PUT',
      body: req,
    })
  }

  // Delete a pattern
  async function deletePattern(patternId: string): Promise<void> {
    await authFetch(`/api/recurring/patterns/${patternId}`, {
      method: 'DELETE',
    })
  }

  // ---------------------------------------------------------------------------
  // Status Actions
  // ---------------------------------------------------------------------------

  // Accept a pending pattern (pending → active)
  async function acceptPattern(patternId: string): Promise<RecurringPattern> {
    return authFetch<RecurringPattern>(
      `/api/recurring/patterns/${patternId}/accept`,
      {
        method: 'POST',
      },
    )
  }

  // Pause an active pattern (active → paused)
  async function pausePattern(patternId: string): Promise<RecurringPattern> {
    return authFetch<RecurringPattern>(
      `/api/recurring/patterns/${patternId}/pause`,
      {
        method: 'POST',
      },
    )
  }

  // Resume a paused pattern (paused → active)
  async function resumePattern(patternId: string): Promise<RecurringPattern> {
    return authFetch<RecurringPattern>(
      `/api/recurring/patterns/${patternId}/resume`,
      {
        method: 'POST',
      },
    )
  }

  // Cancel a pattern (→ cancelled)
  async function cancelPattern(patternId: string): Promise<RecurringPattern> {
    return authFetch<RecurringPattern>(
      `/api/recurring/patterns/${patternId}/cancel`,
      {
        method: 'POST',
      },
    )
  }

  // Re-run matching for a pattern
  async function relinkPattern(patternId: string): Promise<RecurringPattern> {
    return authFetch<RecurringPattern>(
      `/api/recurring/patterns/${patternId}/relink`,
      {
        method: 'POST',
      },
    )
  }

  // ---------------------------------------------------------------------------
  // Create from Transactions
  // ---------------------------------------------------------------------------

  // Create pattern from selected transactions
  async function createFromTransactions(
    req: CreateFromTransactionsRequest,
  ): Promise<RecurringPattern> {
    return authFetch<RecurringPattern>(
      '/api/recurring/patterns/from-transactions',
      {
        method: 'POST',
        body: req,
      },
    )
  }

  // ---------------------------------------------------------------------------
  // Transaction Links
  // ---------------------------------------------------------------------------

  // Manually link a transaction to a pattern
  async function linkTransaction(
    patternId: string,
    transactionId: string,
  ): Promise<void> {
    await authFetch(`/api/recurring/patterns/${patternId}/transactions`, {
      method: 'POST',
      body: { transaction_id: transactionId },
    })
  }

  // Unlink a transaction from a pattern
  async function unlinkTransaction(
    patternId: string,
    transactionId: string,
  ): Promise<void> {
    await authFetch(
      `/api/recurring/patterns/${patternId}/transactions/${transactionId}`,
      {
        method: 'DELETE',
      },
    )
  }

  // ---------------------------------------------------------------------------
  // Upcoming Bills
  // ---------------------------------------------------------------------------

  // Fetch upcoming bills within a date range
  async function fetchUpcomingBills(
    days: number = 7,
  ): Promise<UpcomingBillsResponse> {
    return authFetch<UpcomingBillsResponse>(
      `/api/recurring/upcoming?days=${days}`,
    )
  }

  // ---------------------------------------------------------------------------
  // Summary Statistics
  // ---------------------------------------------------------------------------

  // Fetch recurring patterns summary statistics
  async function fetchSummary(): Promise<RecurringSummary> {
    return authFetch<RecurringSummary>('/api/recurring/summary')
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    // CRUD
    fetchPatterns,
    createPattern,
    fetchPattern,
    fetchPatternTransactions,
    updatePattern,
    deletePattern,

    // Status actions
    acceptPattern,
    pausePattern,
    resumePattern,
    cancelPattern,
    relinkPattern,

    // Create from transactions
    createFromTransactions,

    // Transaction links
    linkTransaction,
    unlinkTransaction,

    // Upcoming bills
    fetchUpcomingBills,

    // Summary
    fetchSummary,

    // Export ApiError for error type checking
    ApiError,
  }
}
