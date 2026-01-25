// =============================================================================
// Authenticated Fetch Composable
// Wraps $fetch with automatic token refresh and auth headers
// =============================================================================

import { useAuthStore } from '~/stores/auth'

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

// Custom error for API errors - includes status code for handling
export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

// -----------------------------------------------------------------------------
// Composable Definition
// -----------------------------------------------------------------------------

export function useAuthenticatedFetch() {
  const config = useRuntimeConfig()
  const authStore = useAuthStore()

  /**
   * Make an authenticated API request.
   * - Refreshes token if expired before making request
   * - Retries once on 401 after refreshing token
   * - Redirects to login if auth completely fails
   * - Sets Authorization header with Bearer token
   * - Sets credentials: 'include' for cookie handling
   *
   * @param path - API path (e.g. '/api/accounts')
   * @param options - Optional fetch options (method, body, etc.)
   * @param isRetry - Whether it is a retry request
   * @returns Promise with typed response
   * @throws ApiError for HTTP errors, includes status code
   */
  async function authFetch<T>(
    path: string,
    options: {
      method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      body?: Record<string, any>
    } = {},
    isRetry = false,
  ): Promise<T> {
    // Refresh token if expired (has 30 second buffer built in)
    if (authStore.isTokenExpired) {
      try {
        await authStore.refreshToken()
      } catch {
        // Refresh failed - redirect to login
        await navigateTo('/login')
        throw new ApiError('Session expired', 401)
      }
    }

    const url = `${config.public.apiUrl}${path}`
    const method = options.method || 'GET'

    try {
      return await $fetch<T>(url, {
        method,
        credentials: 'include',
        headers: {
          Authorization: `Bearer ${authStore.accessToken}`,
        },
        body: options.body,
      })
    } catch (error: unknown) {
      // Extract status code from fetch error
      if (
        error &&
        typeof error === 'object' &&
        'response' in error &&
        error.response &&
        typeof error.response === 'object' &&
        'status' in error.response
      ) {
        const response = error.response as {
          status: number
          _data?: { detail?: string }
        }
        const status = response.status

        // On 401, try refreshing token once and retry the request
        if (status === 401 && !isRetry) {
          try {
            await authStore.refreshToken()
            return authFetch<T>(path, options, true)
          } catch {
            // Refresh failed - redirect to login
            await navigateTo('/login')
            throw new ApiError('Session expired', 401)
          }
        }

        const message =
          response._data?.detail || `Request failed with status ${status}`
        throw new ApiError(message, status)
      }

      // Re-throw unknown errors
      throw error
    }
  }

  return { authFetch, ApiError }
}
