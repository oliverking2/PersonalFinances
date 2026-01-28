// =============================================================================
// Goals API Composable
// All API functions for managing savings goals
// =============================================================================

import type {
  Goal,
  GoalListResponse,
  GoalCreateRequest,
  GoalUpdateRequest,
  GoalContributeRequest,
  GoalSummaryResponse,
} from '~/types/goals'
import {
  useAuthenticatedFetch,
  ApiError,
} from '~/composables/useAuthenticatedFetch'

// -----------------------------------------------------------------------------
// Composable Definition
// -----------------------------------------------------------------------------

export function useGoalsApi() {
  const { authFetch } = useAuthenticatedFetch()

  // ---------------------------------------------------------------------------
  // Goals CRUD
  // ---------------------------------------------------------------------------

  // Fetch all goals for the current user
  async function fetchGoals(
    includeInactive: boolean = false,
  ): Promise<GoalListResponse> {
    const url = includeInactive
      ? '/api/goals?include_inactive=true'
      : '/api/goals'
    return authFetch<GoalListResponse>(url)
  }

  // Get a single goal by ID
  async function fetchGoal(goalId: string): Promise<Goal> {
    return authFetch<Goal>(`/api/goals/${goalId}`)
  }

  // Create a new savings goal
  async function createGoal(req: GoalCreateRequest): Promise<Goal> {
    return authFetch<Goal>('/api/goals', {
      method: 'POST',
      body: req,
    })
  }

  // Update a goal's details
  async function updateGoal(
    goalId: string,
    req: GoalUpdateRequest,
  ): Promise<Goal> {
    return authFetch<Goal>(`/api/goals/${goalId}`, {
      method: 'PUT',
      body: req,
    })
  }

  // Delete a goal
  async function deleteGoal(goalId: string): Promise<void> {
    await authFetch(`/api/goals/${goalId}`, {
      method: 'DELETE',
    })
  }

  // ---------------------------------------------------------------------------
  // Goal Actions
  // ---------------------------------------------------------------------------

  // Add a contribution to a goal
  async function contributeToGoal(
    goalId: string,
    req: GoalContributeRequest,
  ): Promise<Goal> {
    return authFetch<Goal>(`/api/goals/${goalId}/contribute`, {
      method: 'POST',
      body: req,
    })
  }

  // Mark a goal as completed
  async function completeGoal(goalId: string): Promise<Goal> {
    return authFetch<Goal>(`/api/goals/${goalId}/complete`, {
      method: 'PUT',
    })
  }

  // Pause a goal
  async function pauseGoal(goalId: string): Promise<Goal> {
    return authFetch<Goal>(`/api/goals/${goalId}/pause`, {
      method: 'PUT',
    })
  }

  // Resume a paused goal
  async function resumeGoal(goalId: string): Promise<Goal> {
    return authFetch<Goal>(`/api/goals/${goalId}/resume`, {
      method: 'PUT',
    })
  }

  // Cancel a goal
  async function cancelGoal(goalId: string): Promise<Goal> {
    return authFetch<Goal>(`/api/goals/${goalId}/cancel`, {
      method: 'PUT',
    })
  }

  // ---------------------------------------------------------------------------
  // Summary Statistics
  // ---------------------------------------------------------------------------

  // Fetch goals summary statistics
  async function fetchGoalSummary(): Promise<GoalSummaryResponse> {
    return authFetch<GoalSummaryResponse>('/api/goals/summary')
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    // CRUD
    fetchGoals,
    fetchGoal,
    createGoal,
    updateGoal,
    deleteGoal,

    // Actions
    contributeToGoal,
    completeGoal,
    pauseGoal,
    resumeGoal,
    cancelGoal,

    // Summary
    fetchGoalSummary,

    // Export ApiError for error type checking
    ApiError,
  }
}
