// =============================================================================
// Milestones API Composable
// All API functions for managing financial milestones
// =============================================================================

import type {
  Milestone,
  MilestoneListResponse,
  MilestoneCreateRequest,
  MilestoneUpdateRequest,
} from '~/types/milestones'
import {
  useAuthenticatedFetch,
  ApiError,
} from '~/composables/useAuthenticatedFetch'

// -----------------------------------------------------------------------------
// Composable Definition
// -----------------------------------------------------------------------------

export function useMilestonesApi() {
  const { authFetch } = useAuthenticatedFetch()

  // ---------------------------------------------------------------------------
  // Milestones CRUD
  // ---------------------------------------------------------------------------

  // Fetch all milestones for the current user
  // achieved: true = only achieved, false = only pending, undefined = all
  async function fetchMilestones(
    achieved?: boolean,
  ): Promise<MilestoneListResponse> {
    const params = new URLSearchParams()
    if (achieved !== undefined) {
      params.set('achieved', String(achieved))
    }
    const query = params.toString()
    const url = query ? `/api/milestones?${query}` : '/api/milestones'
    return authFetch<MilestoneListResponse>(url)
  }

  // Get a single milestone by ID
  async function fetchMilestone(milestoneId: string): Promise<Milestone> {
    return authFetch<Milestone>(`/api/milestones/${milestoneId}`)
  }

  // Create a new milestone
  async function createMilestone(
    req: MilestoneCreateRequest,
  ): Promise<Milestone> {
    return authFetch<Milestone>('/api/milestones', {
      method: 'POST',
      body: req,
    })
  }

  // Update a milestone
  async function updateMilestone(
    milestoneId: string,
    req: MilestoneUpdateRequest,
  ): Promise<Milestone> {
    return authFetch<Milestone>(`/api/milestones/${milestoneId}`, {
      method: 'PATCH',
      body: req,
    })
  }

  // Delete a milestone
  async function deleteMilestone(milestoneId: string): Promise<void> {
    await authFetch(`/api/milestones/${milestoneId}`, {
      method: 'DELETE',
    })
  }

  // ---------------------------------------------------------------------------
  // Milestone Actions
  // ---------------------------------------------------------------------------

  // Mark a milestone as achieved
  async function achieveMilestone(milestoneId: string): Promise<Milestone> {
    return authFetch<Milestone>(`/api/milestones/${milestoneId}/achieve`, {
      method: 'POST',
    })
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    // CRUD
    fetchMilestones,
    fetchMilestone,
    createMilestone,
    updateMilestone,
    deleteMilestone,

    // Actions
    achieveMilestone,

    // Export ApiError for error type checking
    ApiError,
  }
}
