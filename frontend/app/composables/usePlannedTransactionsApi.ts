// =============================================================================
// Planned Transactions API Composable
// API functions for managing planned transactions (income and expenses)
// =============================================================================

import type {
  PlannedTransaction,
  PlannedTransactionCreateRequest,
  PlannedTransactionListResponse,
  PlannedTransactionSummary,
  PlannedTransactionUpdateRequest,
} from '~/types/planned-transactions'
import { useAuthenticatedFetch } from '~/composables/useAuthenticatedFetch'

// -----------------------------------------------------------------------------
// Composable Definition
// -----------------------------------------------------------------------------

export function usePlannedTransactionsApi() {
  const { authFetch } = useAuthenticatedFetch()

  // ---------------------------------------------------------------------------
  // List & Summary
  // ---------------------------------------------------------------------------

  /**
   * Fetch all planned transactions for the current user.
   * @param direction - Optional filter by 'income' or 'expense'
   * @param enabledOnly - If true, only return enabled transactions
   */
  async function fetchPlannedTransactions(
    direction?: 'income' | 'expense',
    enabledOnly?: boolean,
  ): Promise<PlannedTransactionListResponse> {
    const params = new URLSearchParams()
    if (direction) params.set('direction', direction)
    if (enabledOnly) params.set('enabled_only', 'true')

    const queryStr = params.toString()
    const url = queryStr
      ? `/api/planned-transactions?${queryStr}`
      : '/api/planned-transactions'

    return authFetch<PlannedTransactionListResponse>(url)
  }

  /**
   * Fetch summary statistics for planned transactions.
   */
  async function fetchPlannedSummary(): Promise<PlannedTransactionSummary> {
    return authFetch<PlannedTransactionSummary>(
      '/api/planned-transactions/summary',
    )
  }

  // ---------------------------------------------------------------------------
  // CRUD Operations
  // ---------------------------------------------------------------------------

  /**
   * Get a single planned transaction by ID.
   */
  async function fetchPlannedTransaction(
    id: string,
  ): Promise<PlannedTransaction> {
    return authFetch<PlannedTransaction>(`/api/planned-transactions/${id}`)
  }

  /**
   * Create a new planned transaction.
   */
  async function createPlannedTransaction(
    request: PlannedTransactionCreateRequest,
  ): Promise<PlannedTransaction> {
    return authFetch<PlannedTransaction>('/api/planned-transactions', {
      method: 'POST',
      body: request,
    })
  }

  /**
   * Update an existing planned transaction.
   */
  async function updatePlannedTransaction(
    id: string,
    request: PlannedTransactionUpdateRequest,
  ): Promise<PlannedTransaction> {
    return authFetch<PlannedTransaction>(`/api/planned-transactions/${id}`, {
      method: 'PUT',
      body: request,
    })
  }

  /**
   * Delete a planned transaction.
   */
  async function deletePlannedTransaction(id: string): Promise<void> {
    await authFetch(`/api/planned-transactions/${id}`, {
      method: 'DELETE',
    })
  }

  /**
   * Toggle enabled/disabled state of a planned transaction.
   */
  async function togglePlannedTransaction(
    id: string,
    enabled: boolean,
  ): Promise<PlannedTransaction> {
    return updatePlannedTransaction(id, { enabled })
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  return {
    // List & Summary
    fetchPlannedTransactions,
    fetchPlannedSummary,

    // CRUD
    fetchPlannedTransaction,
    createPlannedTransaction,
    updatePlannedTransaction,
    deletePlannedTransaction,

    // Helpers
    togglePlannedTransaction,
  }
}
