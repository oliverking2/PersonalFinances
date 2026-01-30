// =============================================================================
// Trading 212 API Composable
// API functions for Trading 212 connections
// =============================================================================

import type { Job } from '~/types/jobs'
import {
  useAuthenticatedFetch,
  ApiError,
} from '~/composables/useAuthenticatedFetch'

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

export interface T212Connection {
  id: string
  friendly_name: string
  t212_account_id: string | null
  currency_code: string | null
  status: 'active' | 'error'
  error_message: string | null
  last_synced_at: string | null
  created_at: string
}

export interface T212ConnectionListResponse {
  connections: T212Connection[]
  total: number
}

export interface AddT212ConnectionRequest {
  api_key: string
  friendly_name: string
}

export interface T212CashBalance {
  free: string
  blocked: string
  invested: string
  pie_cash: string
  ppl: string
  result: string
  total: string
  fetched_at: string
}

// -----------------------------------------------------------------------------
// Composable Definition
// -----------------------------------------------------------------------------

export function useTrading212Api() {
  const { authFetch } = useAuthenticatedFetch()

  // ---------------------------------------------------------------------------
  // Connections API
  // ---------------------------------------------------------------------------

  // Fetch all Trading 212 connections
  async function fetchT212Connections(): Promise<T212ConnectionListResponse> {
    return authFetch<T212ConnectionListResponse>('/api/trading212')
  }

  // Add a new Trading 212 connection
  async function addT212Connection(
    req: AddT212ConnectionRequest,
  ): Promise<T212Connection> {
    return authFetch<T212Connection>('/api/trading212', {
      method: 'POST',
      body: req,
    })
  }

  // Get a specific Trading 212 connection
  async function getT212Connection(id: string): Promise<T212Connection> {
    return authFetch<T212Connection>(`/api/trading212/${id}`)
  }

  // Delete a Trading 212 connection
  async function deleteT212Connection(id: string): Promise<void> {
    await authFetch(`/api/trading212/${id}`, {
      method: 'DELETE',
    })
  }

  // Trigger sync for a Trading 212 connection
  async function triggerT212Sync(id: string): Promise<Job> {
    return authFetch<Job>(`/api/trading212/${id}/sync`, {
      method: 'POST',
    })
  }

  // Get latest cash balance for a Trading 212 connection
  async function getT212Balance(id: string): Promise<T212CashBalance> {
    return authFetch<T212CashBalance>(`/api/trading212/${id}/balance`)
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    fetchT212Connections,
    addT212Connection,
    getT212Connection,
    deleteT212Connection,
    triggerT212Sync,
    getT212Balance,

    // Export ApiError for error type checking
    ApiError,
  }
}
