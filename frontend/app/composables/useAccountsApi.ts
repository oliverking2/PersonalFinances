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

  // Update an account's display name
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

    // Export ApiError for error type checking
    ApiError,
  }
}
