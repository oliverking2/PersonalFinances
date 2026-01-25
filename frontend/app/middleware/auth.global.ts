// =============================================================================
// Global Auth Middleware
// Runs on every route change to check authentication status
// =============================================================================
// Validates auth on BOTH server and client:
// - Server: Forwards cookie to API, redirects before HTML is sent if invalid
// - Client: Uses hydrated state or refreshes token on client-side navigation
// =============================================================================

// Types for API responses (duplicated here to avoid import issues in middleware)
interface RefreshResponse {
  access_token: string
  expires_in: number
}

interface User {
  id: string
  username: string
  first_name: string
  last_name: string
}

export default defineNuxtRouteMiddleware(async (to) => {
  // ---------------------------------------------------------------------------
  // Allow public pages (login, etc.) without auth check
  // Pages mark themselves as public via: definePageMeta({ public: true })
  // ---------------------------------------------------------------------------
  if (to.meta.public) {
    return
  }

  const authStore = useAuthStore()
  const config = useRuntimeConfig()

  // ---------------------------------------------------------------------------
  // Server-side: Validate auth by forwarding cookie to backend
  // If valid, populate store (Pinia hydrates to client automatically)
  // If invalid, redirect before any HTML is sent
  // ---------------------------------------------------------------------------
  if (import.meta.server) {
    // Get the cookie header from the incoming request
    const headers = useRequestHeaders(['cookie'])
    const cookieHeader = headers.cookie

    // No cookie at all = definitely not authenticated
    if (!cookieHeader) {
      return navigateTo('/login')
    }

    try {
      // Call /auth/refresh with the cookie forwarded
      // This validates the refresh token and returns a new access token
      const refreshResponse = await $fetch<RefreshResponse>(
        `${config.public.apiUrl}/auth/refresh`,
        {
          method: 'POST',
          headers: {
            cookie: cookieHeader,
          },
        },
      )

      // Fetch user data with the new access token
      const user = await $fetch<User>(`${config.public.apiUrl}/auth/me`, {
        method: 'GET',
        headers: {
          cookie: cookieHeader,
          Authorization: `Bearer ${refreshResponse.access_token}`,
        },
      })

      // Populate the Pinia store - Pinia hydrates this to the client automatically
      // The 30-second buffer in isTokenExpired handles any server/client clock skew
      authStore.$patch({
        user,
        accessToken: refreshResponse.access_token,
        expiresAt: Date.now() + refreshResponse.expires_in * 1000,
      })
    } catch {
      // Refresh failed - cookie invalid, expired, or backend unreachable
      return navigateTo('/login')
    }

    return
  }

  // ---------------------------------------------------------------------------
  // Client-side: Check if we need to refresh the session
  // On initial hydration, store should be populated from SSR
  // On client-side navigation, we may need to refresh if token expired
  // ---------------------------------------------------------------------------
  if (!authStore.isAuthenticated || authStore.isTokenExpired) {
    try {
      // Attempt to refresh - this will:
      // - Get a new access token using the HttpOnly refresh cookie
      // - Fetch user data from /auth/me
      await authStore.refreshToken()
    } catch {
      // Refresh failed - either no valid cookie or token expired
      // Redirect to login
      return navigateTo('/login')
    }
  }

  // ---------------------------------------------------------------------------
  // Final safety check - should have a user after successful refresh
  // ---------------------------------------------------------------------------
  if (!authStore.isAuthenticated) {
    return navigateTo('/login')
  }
})
