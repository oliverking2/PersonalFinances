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

export interface EnumFilter {
  name: string // Column name in the dataset
  label: string // Display label for the filter
  options: string[] // Allowed values
}

export interface NumericFilter {
  name: string // Column name in the dataset
  label: string // Display label for the filter
}

export interface DatasetFilters {
  date_column: string | null
  account_id_column: string | null
  tag_id_column: string | null
  enum_filters: EnumFilter[] // Enum filters with predefined options
  numeric_filters: NumericFilter[] // Numeric filters for range filtering
}

export interface Dataset {
  id: string // UUID
  dataset_name: string // dbt model name (e.g., fct_transactions)
  friendly_name: string // Human-readable name
  description: string
  group: string // facts, dimensions, aggregations
  time_grain: string | null // day, month, etc.
  filters: DatasetFilters // Available filter columns
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

// -----------------------------------------------------------------------------
// Export Types
// -----------------------------------------------------------------------------

export interface EnumFilterValue {
  column: string
  values: string[]
}

export interface NumericFilterValue {
  column: string
  min?: number
  max?: number
}

export interface CreateExportRequest {
  dataset_id: string
  format: 'csv' | 'parquet'
  start_date?: string
  end_date?: string
  account_ids?: string[]
  tag_ids?: string[]
  enum_filters?: EnumFilterValue[]
  numeric_filters?: NumericFilterValue[]
}

export interface CreateExportResponse {
  job_id: string
  status: string
  message: string
}

export interface ExportStatusResponse {
  job_id: string
  status: string // pending, running, completed, failed
  dataset_id: string | null
  dataset_name: string | null
  format: string | null
  row_count: number | null
  file_size_bytes: number | null
  download_url: string | null
  expires_at: string | null
  error_message: string | null
  created_at: string
  completed_at: string | null
}

// Filters stored with an export job
export interface ExportFilters {
  start_date: string | null
  end_date: string | null
  account_ids: string[] | null
  tag_ids: string[] | null
  enum_filters: EnumFilterValue[] | null
  numeric_filters: NumericFilterValue[] | null
}

// Single export in the list response (no download URL - fetched on demand)
export interface ExportListItem {
  job_id: string
  status: string // pending, running, completed, failed
  dataset_id: string | null
  dataset_name: string | null
  format: string | null // csv, parquet
  row_count: number | null
  file_size_bytes: number | null
  error_message: string | null
  created_at: string
  completed_at: string | null
  filters: ExportFilters | null
}

export interface ExportListResponse {
  exports: ExportListItem[]
  total: number
}

// -----------------------------------------------------------------------------
// Forecasting Types
// -----------------------------------------------------------------------------

export interface ForecastDay {
  forecast_date: string // YYYY-MM-DD
  daily_change: string // Decimal as string
  daily_income: string
  daily_expenses: string
  event_count: number
  projected_balance: string
  days_from_now: number
  forecast_week: number
}

export interface ForecastSummary {
  starting_balance: string // Decimal as string
  ending_balance: string
  total_income: string
  total_expenses: string
  net_change: string
  runway_days: number | null // Days until balance goes negative
  min_balance: string
  min_balance_date: string | null
}

export interface CashFlowForecastResponse {
  currency: string
  as_of_date: string // YYYY-MM-DD
  summary: ForecastSummary
  daily: ForecastDay[]
}

export interface ForecastWeek {
  week_number: number
  week_start: string // YYYY-MM-DD
  week_end: string
  total_income: string
  total_expenses: string
  net_change: string
  ending_balance: string
}

export interface WeeklyForecastResponse {
  currency: string
  weeks: ForecastWeek[]
}

// -----------------------------------------------------------------------------
// Forecast Events Types
// -----------------------------------------------------------------------------

export interface ForecastEvent {
  source_type: 'recurring' | 'planned'
  name: string
  amount: string // Decimal as string
  frequency: string | null
}

export interface ForecastEventsResponse {
  forecast_date: string // YYYY-MM-DD
  events: ForecastEvent[]
  event_count: number
}

// Forecast query parameters
export interface ForecastQueryParams {
  start_date?: string // YYYY-MM-DD
  end_date?: string // YYYY-MM-DD
  include_manual_assets?: boolean // Include manual assets in net worth calculation
}

// -----------------------------------------------------------------------------
// Scenario Types
// -----------------------------------------------------------------------------

export interface PatternModification {
  pattern_id: string
  new_amount: string | null // Decimal as string, null = exclude
}

export interface ScenarioRequest {
  exclude_patterns?: string[]
  exclude_planned?: string[]
  modifications?: PatternModification[]
}
