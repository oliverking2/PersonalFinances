// =============================================================================
// Transactions API Composable
// API functions for fetching and filtering transactions
// =============================================================================

import type {
  TransactionListResponse,
  TransactionQueryParams,
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

    if (params.account_id) {
      queryParams.set('account_id', params.account_id)
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
  // Public API
  // ---------------------------------------------------------------------------
  return {
    fetchTransactions,
  }
}
