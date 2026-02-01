// =============================================================================
// Budgets API Composable
// All API functions for managing budgets
// =============================================================================

import type {
  Budget,
  BudgetListResponse,
  BudgetCreateRequest,
  BudgetUpdateRequest,
  BudgetWithSpending,
  BudgetSummaryResponse,
  BudgetForecastResponse,
} from '~/types/budgets'
import {
  useAuthenticatedFetch,
  ApiError,
} from '~/composables/useAuthenticatedFetch'

// -----------------------------------------------------------------------------
// Composable Definition
// -----------------------------------------------------------------------------

export function useBudgetsApi() {
  const { authFetch } = useAuthenticatedFetch()

  // ---------------------------------------------------------------------------
  // Budgets CRUD
  // ---------------------------------------------------------------------------

  // Fetch all budgets for the current user
  async function fetchBudgets(): Promise<BudgetListResponse> {
    return authFetch<BudgetListResponse>('/api/budgets')
  }

  // Get a single budget by ID (includes current spending)
  async function fetchBudget(budgetId: string): Promise<BudgetWithSpending> {
    return authFetch<BudgetWithSpending>(`/api/budgets/${budgetId}`)
  }

  // Create a new budget for a tag
  async function createBudget(req: BudgetCreateRequest): Promise<Budget> {
    return authFetch<Budget>('/api/budgets', {
      method: 'POST',
      body: req,
    })
  }

  // Update a budget's settings
  async function updateBudget(
    budgetId: string,
    req: BudgetUpdateRequest,
  ): Promise<Budget> {
    return authFetch<Budget>(`/api/budgets/${budgetId}`, {
      method: 'PUT',
      body: req,
    })
  }

  // Delete a budget
  async function deleteBudget(budgetId: string): Promise<void> {
    await authFetch(`/api/budgets/${budgetId}`, {
      method: 'DELETE',
    })
  }

  // ---------------------------------------------------------------------------
  // Summary Statistics
  // ---------------------------------------------------------------------------

  // Fetch budget summary statistics
  async function fetchBudgetSummary(): Promise<BudgetSummaryResponse> {
    return authFetch<BudgetSummaryResponse>('/api/budgets/summary')
  }

  // ---------------------------------------------------------------------------
  // Forecast
  // ---------------------------------------------------------------------------

  // Fetch budget forecasts (projections for when budgets will be exhausted)
  async function fetchBudgetForecasts(): Promise<BudgetForecastResponse> {
    return authFetch<BudgetForecastResponse>('/api/budgets/forecast')
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    // CRUD
    fetchBudgets,
    fetchBudget,
    createBudget,
    updateBudget,
    deleteBudget,

    // Summary
    fetchBudgetSummary,

    // Forecast
    fetchBudgetForecasts,

    // Export ApiError for error type checking
    ApiError,
  }
}
