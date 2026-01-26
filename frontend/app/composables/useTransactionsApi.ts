// =============================================================================
// Transactions API Composable
// API functions for fetching and filtering transactions
// =============================================================================

import type {
  Transaction,
  TransactionListResponse,
  TransactionQueryParams,
  TransactionSplitsResponse,
  SetSplitsRequest,
  UpdateNoteRequest,
} from '~/types/transactions'
import { useAuthenticatedFetch } from '~/composables/useAuthenticatedFetch'

// -----------------------------------------------------------------------------
// Composable Definition
// -----------------------------------------------------------------------------

export function useTransactionsApi() {
  const { authFetch } = useAuthenticatedFetch()

  // ---------------------------------------------------------------------------
  // Transactions API
  // ---------------------------------------------------------------------------

  /**
   * Fetch transactions with optional filters and pagination.
   *
   * @param params - Query parameters for filtering
   * @returns Paginated list of transactions
   */
  async function fetchTransactions(
    params: TransactionQueryParams = {},
  ): Promise<TransactionListResponse> {
    // Build query string from params
    const queryParams = new URLSearchParams()

    // Add each account_id as separate query param (account_ids=x&account_ids=y)
    if (params.account_ids && params.account_ids.length > 0) {
      for (const accountId of params.account_ids) {
        queryParams.append('account_ids', accountId)
      }
    }
    if (params.start_date) {
      queryParams.set('start_date', params.start_date)
    }
    if (params.end_date) {
      queryParams.set('end_date', params.end_date)
    }
    if (params.min_amount !== undefined) {
      queryParams.set('min_amount', String(params.min_amount))
    }
    if (params.max_amount !== undefined) {
      queryParams.set('max_amount', String(params.max_amount))
    }
    if (params.search) {
      queryParams.set('search', params.search)
    }
    // Add each tag_id as separate query param (tag_ids=x&tag_ids=y)
    if (params.tag_ids && params.tag_ids.length > 0) {
      for (const tagId of params.tag_ids) {
        queryParams.append('tag_ids', tagId)
      }
    }
    if (params.page) {
      queryParams.set('page', String(params.page))
    }
    if (params.page_size) {
      queryParams.set('page_size', String(params.page_size))
    }

    const queryString = queryParams.toString()
    const path = queryString
      ? `/api/transactions?${queryString}`
      : '/api/transactions'

    return authFetch<TransactionListResponse>(path)
  }

  // ---------------------------------------------------------------------------
  // Split Management
  // ---------------------------------------------------------------------------

  // Get splits for a transaction
  async function getSplits(
    transactionId: string,
  ): Promise<TransactionSplitsResponse> {
    return authFetch<TransactionSplitsResponse>(
      `/api/transactions/${transactionId}/splits`,
    )
  }

  // Set splits for a transaction (replaces all existing splits)
  async function setSplits(
    transactionId: string,
    req: SetSplitsRequest,
  ): Promise<TransactionSplitsResponse> {
    return authFetch<TransactionSplitsResponse>(
      `/api/transactions/${transactionId}/splits`,
      {
        method: 'PUT',
        body: req,
      },
    )
  }

  // Clear all splits from a transaction
  async function clearSplits(transactionId: string): Promise<void> {
    await authFetch(`/api/transactions/${transactionId}/splits`, {
      method: 'DELETE',
    })
  }

  // ---------------------------------------------------------------------------
  // Note Management
  // ---------------------------------------------------------------------------

  // Update or clear the user note on a transaction
  async function updateNote(
    transactionId: string,
    req: UpdateNoteRequest,
  ): Promise<Transaction> {
    return authFetch<Transaction>(`/api/transactions/${transactionId}/note`, {
      method: 'PATCH',
      body: req,
    })
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    fetchTransactions,
    getSplits,
    setSplits,
    clearSplits,
    updateNote,
  }
}
