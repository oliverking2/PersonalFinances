// =============================================================================
// Accounts API Composable
// All API functions for connections, accounts, and institutions
// =============================================================================

import type {
  Connection,
  Account,
  ConnectionListResponse,
  AccountListResponse,
  InstitutionListResponse,
  CreateConnectionRequest,
  CreateConnectionResponse,
  UpdateConnectionRequest,
  UpdateAccountRequest,
  ReauthoriseResponse,
} from '~/types/accounts'
import type { Job, JobListResponse } from '~/types/jobs'
import {
  useAuthenticatedFetch,
  ApiError,
} from '~/composables/useAuthenticatedFetch'

// -----------------------------------------------------------------------------
// Composable Definition
// -----------------------------------------------------------------------------

export function useAccountsApi() {
  const { authFetch } = useAuthenticatedFetch()

  // ---------------------------------------------------------------------------
  // Connections API
  // ---------------------------------------------------------------------------

  // Fetch all connections
  async function fetchConnections(): Promise<ConnectionListResponse> {
    return authFetch<ConnectionListResponse>('/api/connections')
  }

  // Create a new connection (starts bank auth flow)
  // Note: Returns 501 until GoCardless OAuth flow is implemented
  async function createConnection(
    req: CreateConnectionRequest,
  ): Promise<CreateConnectionResponse> {
    return authFetch<CreateConnectionResponse>('/api/connections', {
      method: 'POST',
      body: req,
    })
  }

  // Update a connection's friendly name
  async function updateConnection(
    id: string,
    req: UpdateConnectionRequest,
  ): Promise<Connection> {
    return authFetch<Connection>(`/api/connections/${id}`, {
      method: 'PATCH',
      body: req,
    })
  }

  // Delete a connection and its accounts
  async function deleteConnection(id: string): Promise<void> {
    await authFetch(`/api/connections/${id}`, {
      method: 'DELETE',
    })
  }

  // Reauthorise an expired connection
  // Note: Returns 501 until GoCardless re-auth flow is implemented
  async function reauthoriseConnection(
    id: string,
  ): Promise<ReauthoriseResponse> {
    return authFetch<ReauthoriseResponse>(
      `/api/connections/${id}/reauthorise`,
      {
        method: 'POST',
      },
    )
  }

  // ---------------------------------------------------------------------------
  // Accounts API
  // ---------------------------------------------------------------------------

  // Fetch accounts, optionally filtered by connection
  async function fetchAccounts(
    connectionId?: string,
  ): Promise<AccountListResponse> {
    const query = connectionId ? `?connection_id=${connectionId}` : ''
    return authFetch<AccountListResponse>(`/api/accounts${query}`)
  }

  // Update an account's settings (display name, category, min balance)
  async function updateAccount(
    id: string,
    req: UpdateAccountRequest,
  ): Promise<Account> {
    return authFetch<Account>(`/api/accounts/${id}`, {
      method: 'PATCH',
      body: req,
    })
  }

  // ---------------------------------------------------------------------------
  // Institutions API
  // ---------------------------------------------------------------------------

  // Fetch available institutions (banks)
  async function fetchInstitutions(): Promise<InstitutionListResponse> {
    return authFetch<InstitutionListResponse>('/api/institutions')
  }

  // ---------------------------------------------------------------------------
  // Sync / Jobs API
  // ---------------------------------------------------------------------------

  // Trigger a sync for a specific connection
  // Always uses full_sync=true to ignore watermark and fetch all transaction history
  async function triggerConnectionSync(connectionId: string): Promise<Job> {
    return authFetch<Job>(
      `/api/connections/${connectionId}/sync?full_sync=true`,
      {
        method: 'POST',
      },
    )
  }

  // Get a job by ID (also updates status from job runner if running)
  async function fetchJob(jobId: string): Promise<Job> {
    return authFetch<Job>(`/api/jobs/${jobId}`)
  }

  // List jobs, optionally filtered by entity
  async function fetchJobs(params?: {
    entity_type?: string
    entity_id?: string
    job_type?: string
    status?: string
    limit?: number
    offset?: number
  }): Promise<JobListResponse> {
    const query = new URLSearchParams()
    if (params?.entity_type) query.set('entity_type', params.entity_type)
    if (params?.entity_id) query.set('entity_id', params.entity_id)
    if (params?.job_type) query.set('job_type', params.job_type)
    if (params?.status) query.set('status', params.status)
    if (params?.limit) query.set('limit', params.limit.toString())
    if (params?.offset) query.set('offset', params.offset.toString())

    const queryString = query.toString()
    const url = queryString ? `/api/jobs?${queryString}` : '/api/jobs'
    return authFetch<JobListResponse>(url)
  }

  // Get the most recent sync job for a connection
  async function getLatestSyncJob(connectionId: string): Promise<Job | null> {
    const response = await fetchJobs({
      entity_type: 'connection',
      entity_id: connectionId,
      job_type: 'sync',
      limit: 1,
    })
    return response.jobs[0] || null
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    // Connections
    fetchConnections,
    createConnection,
    updateConnection,
    deleteConnection,
    reauthoriseConnection,

    // Accounts
    fetchAccounts,
    updateAccount,

    // Institutions
    fetchInstitutions,

    // Sync / Jobs
    triggerConnectionSync,
    fetchJob,
    fetchJobs,
    getLatestSyncJob,

    // Export ApiError for error type checking
    ApiError,
  }
}
