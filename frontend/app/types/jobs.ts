// =============================================================================
// Jobs Types
// TypeScript interfaces for background jobs
// =============================================================================

// -----------------------------------------------------------------------------
// Status Enums
// -----------------------------------------------------------------------------

// Job types - what kind of background task
export type JobType = 'sync' | 'export'

// Job status - current execution state
export type JobStatus = 'pending' | 'running' | 'completed' | 'failed'

// -----------------------------------------------------------------------------
// Job Interface
// -----------------------------------------------------------------------------

export interface Job {
  id: string
  job_type: JobType
  status: JobStatus
  entity_type: string | null // e.g. "connection"
  entity_id: string | null // UUID of related entity
  dagster_run_id: string | null // Job runner run ID for tracking
  error_message: string | null // Error details if failed
  created_at: string // ISO timestamp
  started_at: string | null // ISO timestamp
  completed_at: string | null // ISO timestamp
}

// -----------------------------------------------------------------------------
// API Response Types
// -----------------------------------------------------------------------------

export interface JobListResponse {
  jobs: Job[]
  total: number
}
