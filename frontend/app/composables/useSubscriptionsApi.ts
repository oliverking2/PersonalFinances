// =============================================================================
// Subscriptions API Composable
// All API functions for managing recurring patterns/subscriptions
// =============================================================================

import type {
  Subscription,
  SubscriptionListResponse,
  SubscriptionCreateRequest,
  SubscriptionUpdateRequest,
  SubscriptionQueryParams,
  UpcomingBillsResponse,
  SubscriptionSummary,
  SubscriptionTransactionsResponse,
} from '~/types/subscriptions'
import {
  useAuthenticatedFetch,
  ApiError,
} from '~/composables/useAuthenticatedFetch'

// -----------------------------------------------------------------------------
// Composable Definition
// -----------------------------------------------------------------------------

export function useSubscriptionsApi() {
  const { authFetch } = useAuthenticatedFetch()

  // ---------------------------------------------------------------------------
  // Subscriptions CRUD
  // ---------------------------------------------------------------------------

  // Fetch all subscriptions with optional filters
  async function fetchSubscriptions(
    params?: SubscriptionQueryParams,
  ): Promise<SubscriptionListResponse> {
    // Build query string from params
    const query = new URLSearchParams()
    if (params?.status) query.set('status', params.status)
    if (params?.frequency) query.set('frequency', params.frequency)
    if (params?.min_confidence !== undefined)
      query.set('min_confidence', String(params.min_confidence))
    if (params?.include_dismissed)
      query.set('include_dismissed', String(params.include_dismissed))

    const queryStr = query.toString()
    const url = queryStr
      ? `/api/subscriptions?${queryStr}`
      : '/api/subscriptions'

    return authFetch<SubscriptionListResponse>(url)
  }

  // Create a new subscription manually
  async function createSubscription(
    req: SubscriptionCreateRequest,
  ): Promise<Subscription> {
    return authFetch<Subscription>('/api/subscriptions', {
      method: 'POST',
      body: req,
    })
  }

  // Get a single subscription by ID
  async function fetchSubscription(
    subscriptionId: string,
  ): Promise<Subscription> {
    return authFetch<Subscription>(`/api/subscriptions/${subscriptionId}`)
  }

  // Get transactions linked to a subscription
  async function fetchSubscriptionTransactions(
    subscriptionId: string,
  ): Promise<SubscriptionTransactionsResponse> {
    return authFetch<SubscriptionTransactionsResponse>(
      `/api/subscriptions/${subscriptionId}/transactions`,
    )
  }

  // Update a subscription's details or status
  async function updateSubscription(
    subscriptionId: string,
    req: SubscriptionUpdateRequest,
  ): Promise<Subscription> {
    return authFetch<Subscription>(`/api/subscriptions/${subscriptionId}`, {
      method: 'PUT',
      body: req,
    })
  }

  // Dismiss a subscription (marks as not recurring)
  async function dismissSubscription(subscriptionId: string): Promise<void> {
    await authFetch(`/api/subscriptions/${subscriptionId}`, {
      method: 'DELETE',
    })
  }

  // ---------------------------------------------------------------------------
  // Quick Actions
  // ---------------------------------------------------------------------------

  // Confirm a detected subscription as recurring
  async function confirmSubscription(
    subscriptionId: string,
  ): Promise<Subscription> {
    return authFetch<Subscription>(
      `/api/subscriptions/${subscriptionId}/confirm`,
      {
        method: 'PUT',
      },
    )
  }

  // Pause a subscription (temporarily hide from upcoming bills)
  async function pauseSubscription(
    subscriptionId: string,
  ): Promise<Subscription> {
    return authFetch<Subscription>(
      `/api/subscriptions/${subscriptionId}/pause`,
      {
        method: 'PUT',
      },
    )
  }

  // ---------------------------------------------------------------------------
  // Upcoming Bills
  // ---------------------------------------------------------------------------

  // Fetch upcoming bills within a date range
  async function fetchUpcomingBills(
    days: number = 7,
  ): Promise<UpcomingBillsResponse> {
    return authFetch<UpcomingBillsResponse>(
      `/api/subscriptions/upcoming?days=${days}`,
    )
  }

  // ---------------------------------------------------------------------------
  // Summary Statistics
  // ---------------------------------------------------------------------------

  // Fetch subscription summary statistics
  async function fetchSubscriptionSummary(): Promise<SubscriptionSummary> {
    return authFetch<SubscriptionSummary>('/api/subscriptions/summary')
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    // CRUD
    fetchSubscriptions,
    createSubscription,
    fetchSubscription,
    fetchSubscriptionTransactions,
    updateSubscription,
    dismissSubscription,

    // Quick actions
    confirmSubscription,
    pauseSubscription,

    // Upcoming bills
    fetchUpcomingBills,

    // Summary
    fetchSubscriptionSummary,

    // Export ApiError for error type checking
    ApiError,
  }
}
