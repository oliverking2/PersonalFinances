// =============================================================================
// Analytics API Composable
// API functions for querying analytics datasets and managing refresh
// =============================================================================

import type {
  AnalyticsStatus,
  CashFlowForecastResponse,
  Dataset,
  DatasetListResponse,
  DatasetQueryParams,
  DatasetQueryResponse,
  DatasetWithSchema,
  ForecastEventsResponse,
  ForecastQueryParams,
  RefreshResponse,
  ScenarioRequest,
  WeeklyForecastResponse,
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
  // Forecasting API
  // ---------------------------------------------------------------------------

  /**
   * Fetch cash flow forecast for a configurable date range.
   * Returns daily projections with income, expenses, and projected balances.
   *
   * @param params - Optional date range (defaults to today + 90 days)
   */
  async function fetchForecast(
    params?: ForecastQueryParams,
  ): Promise<CashFlowForecastResponse> {
    const queryParams = new URLSearchParams()

    if (params?.start_date) {
      queryParams.set('start_date', params.start_date)
    }
    if (params?.end_date) {
      queryParams.set('end_date', params.end_date)
    }

    const queryString = queryParams.toString()
    const path = queryString
      ? `/api/analytics/forecast?${queryString}`
      : '/api/analytics/forecast'

    return authFetch<CashFlowForecastResponse>(path)
  }

  /**
   * Fetch weekly aggregated forecast data for a configurable date range.
   * Returns weekly summaries for easier visualisation.
   *
   * @param params - Optional date range (defaults to today + 90 days)
   */
  async function fetchWeeklyForecast(
    params?: ForecastQueryParams,
  ): Promise<WeeklyForecastResponse> {
    const queryParams = new URLSearchParams()

    if (params?.start_date) {
      queryParams.set('start_date', params.start_date)
    }
    if (params?.end_date) {
      queryParams.set('end_date', params.end_date)
    }

    const queryString = queryParams.toString()
    const path = queryString
      ? `/api/analytics/forecast/weekly?${queryString}`
      : '/api/analytics/forecast/weekly'

    return authFetch<WeeklyForecastResponse>(path)
  }

  /**
   * Fetch detailed events for a specific forecast date.
   * Returns list of recurring patterns and planned transactions for the date.
   *
   * @param forecastDate - The date to get events for (YYYY-MM-DD)
   */
  async function fetchForecastEvents(
    forecastDate: string,
  ): Promise<ForecastEventsResponse> {
    return authFetch<ForecastEventsResponse>(
      `/api/analytics/forecast/events?forecast_date=${forecastDate}`,
    )
  }

  /**
   * Calculate a 'what-if' forecast scenario.
   * Allows excluding patterns or modifying amounts to see projected impact.
   */
  async function calculateScenario(
    scenario: ScenarioRequest,
  ): Promise<CashFlowForecastResponse> {
    return authFetch<CashFlowForecastResponse>(
      '/api/analytics/forecast/scenario',
      {
        method: 'POST',
        body: scenario,
      },
    )
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

    // Forecasting
    fetchForecast,
    fetchWeeklyForecast,
    fetchForecastEvents,
    calculateScenario,
  }
}
