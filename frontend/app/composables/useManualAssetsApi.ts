// =============================================================================
// Manual Assets API Composable
// All API functions for managing manual assets and liabilities
// =============================================================================

import type {
  ManualAsset,
  ManualAssetListResponse,
  ManualAssetSummaryResponse,
  ManualAssetCreateRequest,
  ManualAssetUpdateRequest,
  ValueUpdateRequest,
  ValueHistoryResponse,
} from '~/types/manual-assets'
import {
  useAuthenticatedFetch,
  ApiError,
} from '~/composables/useAuthenticatedFetch'

// -----------------------------------------------------------------------------
// Composable Definition
// -----------------------------------------------------------------------------

export function useManualAssetsApi() {
  const { authFetch } = useAuthenticatedFetch()

  // ---------------------------------------------------------------------------
  // Manual Assets CRUD
  // ---------------------------------------------------------------------------

  // Fetch all manual assets for the current user
  async function fetchManualAssets(
    options: {
      includeInactive?: boolean
      isLiability?: boolean | null
    } = {},
  ): Promise<ManualAssetListResponse> {
    const params = new URLSearchParams()
    if (options.includeInactive) {
      params.set('include_inactive', 'true')
    }
    if (options.isLiability !== undefined && options.isLiability !== null) {
      params.set('is_liability', String(options.isLiability))
    }
    const queryString = params.toString()
    const url = queryString
      ? `/api/manual-assets?${queryString}`
      : '/api/manual-assets'
    return authFetch<ManualAssetListResponse>(url)
  }

  // Get a single manual asset by ID
  async function fetchManualAsset(assetId: string): Promise<ManualAsset> {
    return authFetch<ManualAsset>(`/api/manual-assets/${assetId}`)
  }

  // Create a new manual asset
  async function createManualAsset(
    req: ManualAssetCreateRequest,
  ): Promise<ManualAsset> {
    return authFetch<ManualAsset>('/api/manual-assets', {
      method: 'POST',
      body: req,
    })
  }

  // Update a manual asset's details (not value)
  async function updateManualAsset(
    assetId: string,
    req: ManualAssetUpdateRequest,
  ): Promise<ManualAsset> {
    return authFetch<ManualAsset>(`/api/manual-assets/${assetId}`, {
      method: 'PATCH',
      body: req,
    })
  }

  // Delete a manual asset
  async function deleteManualAsset(
    assetId: string,
    hardDelete: boolean = false,
  ): Promise<void> {
    const url = hardDelete
      ? `/api/manual-assets/${assetId}?hard_delete=true`
      : `/api/manual-assets/${assetId}`
    await authFetch(url, {
      method: 'DELETE',
    })
  }

  // ---------------------------------------------------------------------------
  // Value Updates
  // ---------------------------------------------------------------------------

  // Update a manual asset's value (creates a history snapshot)
  async function updateManualAssetValue(
    assetId: string,
    req: ValueUpdateRequest,
  ): Promise<ManualAsset> {
    return authFetch<ManualAsset>(
      `/api/manual-assets/${assetId}/update-value`,
      {
        method: 'POST',
        body: req,
      },
    )
  }

  // Get value history for a manual asset
  async function fetchValueHistory(
    assetId: string,
    limit: number = 100,
  ): Promise<ValueHistoryResponse> {
    return authFetch<ValueHistoryResponse>(
      `/api/manual-assets/${assetId}/history?limit=${limit}`,
    )
  }

  // ---------------------------------------------------------------------------
  // Summary Statistics
  // ---------------------------------------------------------------------------

  // Fetch summary totals (assets, liabilities, net impact)
  async function fetchManualAssetsSummary(): Promise<ManualAssetSummaryResponse> {
    return authFetch<ManualAssetSummaryResponse>('/api/manual-assets/summary')
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    // CRUD
    fetchManualAssets,
    fetchManualAsset,
    createManualAsset,
    updateManualAsset,
    deleteManualAsset,

    // Value updates
    updateManualAssetValue,
    fetchValueHistory,

    // Summary
    fetchManualAssetsSummary,

    // Export ApiError for error type checking
    ApiError,
  }
}
