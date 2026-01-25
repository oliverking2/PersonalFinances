// =============================================================================
// Analytics Types
// TypeScript interfaces for analytics API responses
// =============================================================================

// -----------------------------------------------------------------------------
// Dataset Types
// -----------------------------------------------------------------------------

export interface DatasetColumn {
  name: string
  description: string
  data_type: string | null
}

export interface Dataset {
  id: string // UUID
  dataset_name: string // dbt model name (e.g., fct_transactions)
  friendly_name: string // Human-readable name
  description: string
  group: string // facts, dimensions, aggregations
  time_grain: string | null // day, month, etc.
}

export interface DatasetWithSchema extends Dataset {
  columns: DatasetColumn[]
}

// -----------------------------------------------------------------------------
// Query Types
// -----------------------------------------------------------------------------

export interface DatasetQueryParams {
  start_date?: string // YYYY-MM-DD
  end_date?: string // YYYY-MM-DD
  account_ids?: string[] // Filter by account UUIDs
  tag_ids?: string[] // Filter by tag UUIDs
  limit?: number // Max rows (default 1000)
  offset?: number // Pagination offset
}

export interface DatasetQueryResponse {
  dataset_id: string
  dataset_name: string
  rows: Record<string, unknown>[] // Dynamic row data
  row_count: number
  filters_applied: Record<string, unknown>
}

// -----------------------------------------------------------------------------
// Status & Refresh Types
// -----------------------------------------------------------------------------

export interface AnalyticsStatus {
  duckdb_available: boolean
  manifest_available: boolean
  dataset_count: number
  last_refresh: string | null // ISO timestamp
}

export interface RefreshResponse {
  job_id: string
  dagster_run_id: string | null
  status: string
  message: string
}

// -----------------------------------------------------------------------------
// API Response Types
// -----------------------------------------------------------------------------

export interface DatasetListResponse {
  datasets: Dataset[]
  total: number
}
