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

  // Fetch all budgets for the current user, optionally for a historical period
  async function fetchBudgets(
    referenceDate?: string,
  ): Promise<BudgetListResponse> {
    const query = referenceDate ? `?reference_date=${referenceDate}` : ''
    return authFetch<BudgetListResponse>(`/api/budgets${query}`)
  }

  // Get a single budget by ID (includes spending for the given period)
  async function fetchBudget(
    budgetId: string,
    referenceDate?: string,
  ): Promise<BudgetWithSpending> {
    const query = referenceDate ? `?reference_date=${referenceDate}` : ''
    return authFetch<BudgetWithSpending>(`/api/budgets/${budgetId}${query}`)
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

  // Fetch budget summary statistics, optionally for a historical period
  async function fetchBudgetSummary(
    referenceDate?: string,
  ): Promise<BudgetSummaryResponse> {
    const query = referenceDate ? `?reference_date=${referenceDate}` : ''
    return authFetch<BudgetSummaryResponse>(`/api/budgets/summary${query}`)
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
