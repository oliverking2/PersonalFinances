// =============================================================================
// Exports API Composable
// API functions for creating and monitoring dataset exports
// =============================================================================

import type {
  CreateExportRequest,
  CreateExportResponse,
  ExportListResponse,
  ExportStatusResponse,
} from '~/types/analytics'
import { useAuthenticatedFetch } from '~/composables/useAuthenticatedFetch'

// -----------------------------------------------------------------------------
// Composable Definition
// -----------------------------------------------------------------------------

export function useExportsApi() {
  const { authFetch } = useAuthenticatedFetch()

  // ---------------------------------------------------------------------------
  // List Exports
  // ---------------------------------------------------------------------------

  /**
   * List all export jobs for the current user.
   * Returns exports sorted by creation date (newest first).
   */
  async function listExports(): Promise<ExportListResponse> {
    return authFetch<ExportListResponse>('/api/analytics/exports')
  }

  // ---------------------------------------------------------------------------
  // Create Export
  // ---------------------------------------------------------------------------

  /**
   * Create a new dataset export job.
   * Returns a job ID that can be polled for status.
   *
   * @param request - Export request with dataset ID, format, and filters
   */
  async function createExport(
    request: CreateExportRequest,
  ): Promise<CreateExportResponse> {
    return authFetch<CreateExportResponse>('/api/analytics/exports', {
      method: 'POST',
      body: request,
    })
  }

  // ---------------------------------------------------------------------------
  // Get Export Status
  // ---------------------------------------------------------------------------

  /**
   * Get the status of an export job.
   * Returns download URL when the export is complete.
   *
   * @param jobId - The job UUID to check
   */
  async function getExportStatus(jobId: string): Promise<ExportStatusResponse> {
    return authFetch<ExportStatusResponse>(`/api/analytics/exports/${jobId}`)
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  return {
    listExports,
    createExport,
    getExportStatus,
  }
}
