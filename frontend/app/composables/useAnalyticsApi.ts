// =============================================================================
// Analytics API Composable
// API functions for querying analytics datasets and managing refresh
// =============================================================================

import type {
  AnalyticsStatus,
  Dataset,
  DatasetListResponse,
  DatasetQueryParams,
  DatasetQueryResponse,
  DatasetWithSchema,
  RefreshResponse,
} from '~/types/analytics'
import { useAuthenticatedFetch } from '~/composables/useAuthenticatedFetch'

// -----------------------------------------------------------------------------
// Composable Definition
// -----------------------------------------------------------------------------

export function useAnalyticsApi() {
  const { authFetch } = useAuthenticatedFetch()

  // ---------------------------------------------------------------------------
  // Status API
  // ---------------------------------------------------------------------------

  /**
   * Check analytics system status (DuckDB, manifest availability).
   */
  async function fetchAnalyticsStatus(): Promise<AnalyticsStatus> {
    return authFetch<AnalyticsStatus>('/api/analytics/status')
  }

  // ---------------------------------------------------------------------------
  // Dataset Discovery API
  // ---------------------------------------------------------------------------

  /**
   * List all available analytics datasets.
   */
  async function fetchDatasets(): Promise<DatasetListResponse> {
    return authFetch<DatasetListResponse>('/api/analytics/datasets')
  }

  /**
   * Get schema details for a specific dataset.
   */
  async function fetchDatasetSchema(
    datasetId: string,
  ): Promise<DatasetWithSchema> {
    return authFetch<DatasetWithSchema>(
      `/api/analytics/datasets/${datasetId}/schema`,
    )
  }

  // ---------------------------------------------------------------------------
  // Query API
  // ---------------------------------------------------------------------------

  /**
   * Query a dataset with optional filters.
   *
   * @param datasetId - UUID of the dataset to query
   * @param params - Optional query parameters (date range, filters, pagination)
   */
  async function queryDataset(
    datasetId: string,
    params: DatasetQueryParams = {},
  ): Promise<DatasetQueryResponse> {
    // Build query string from params
    const queryParams = new URLSearchParams()

    if (params.start_date) {
      queryParams.set('start_date', params.start_date)
    }
    if (params.end_date) {
      queryParams.set('end_date', params.end_date)
    }
    // Add each account_id as separate query param
    if (params.account_ids && params.account_ids.length > 0) {
      for (const accountId of params.account_ids) {
        queryParams.append('account_ids', accountId)
      }
    }
    // Add each tag_id as separate query param
    if (params.tag_ids && params.tag_ids.length > 0) {
      for (const tagId of params.tag_ids) {
        queryParams.append('tag_ids', tagId)
      }
    }
    if (params.limit !== undefined) {
      queryParams.set('limit', String(params.limit))
    }
    if (params.offset !== undefined) {
      queryParams.set('offset', String(params.offset))
    }

    const queryString = queryParams.toString()
    const path = queryString
      ? `/api/analytics/datasets/${datasetId}/query?${queryString}`
      : `/api/analytics/datasets/${datasetId}/query`

    return authFetch<DatasetQueryResponse>(path)
  }

  // ---------------------------------------------------------------------------
  // Refresh API
  // ---------------------------------------------------------------------------

  /**
   * Trigger an analytics refresh (dbt rebuild).
   * Returns a job ID that can be polled for status.
   */
  async function triggerRefresh(): Promise<RefreshResponse> {
    return authFetch<RefreshResponse>('/api/analytics/refresh', {
      method: 'POST',
    })
  }

  // ---------------------------------------------------------------------------
  // Helper: Find dataset by name
  // ---------------------------------------------------------------------------

  /**
   * Find a dataset by its dbt model name (e.g., 'fct_monthly_trends').
   * Returns the dataset if found, or undefined if not.
   */
  async function findDatasetByName(name: string): Promise<Dataset | undefined> {
    const response = await fetchDatasets()
    return response.datasets.find((ds) => ds.dataset_name === name)
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    // Status
    fetchAnalyticsStatus,

    // Datasets
    fetchDatasets,
    fetchDatasetSchema,
    findDatasetByName,

    // Query
    queryDataset,

    // Refresh
    triggerRefresh,
  }
}
