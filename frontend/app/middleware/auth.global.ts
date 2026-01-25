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

    // Check if we have the refresh_token cookie
    // In local dev, cookie won't be sent because frontend (port 3000) and backend (port 8000)
    // are different origins. In production, COOKIE_DOMAIN must be set to share across subdomains.
    if (!cookieHeader || !cookieHeader.includes('refresh_token=')) {
      if (import.meta.dev) {
        // Dev mode: skip SSR auth, let client-side handle it (avoids flash to login)
        return
      }
      // Production: no cookie means not authenticated
      return navigateTo('/login')
    }

    try {
      // Call /auth/refresh with the cookie forwarded
      // This validates the refresh token and returns a new access token
      // IMPORTANT: Backend rotates the refresh token on each call, so we must
      // capture the Set-Cookie header and forward it to the browser
      const refreshResponse = await $fetch.raw<RefreshResponse>(
        `${config.public.apiUrl}/auth/refresh`,
        {
          method: 'POST',
          headers: {
            cookie: cookieHeader,
          },
        },
      )

      // Forward the Set-Cookie header from backend to browser
      // This is critical because backend rotates the refresh token on each refresh
      const setCookie = refreshResponse.headers.get('set-cookie')
      if (setCookie) {
        appendResponseHeader(useRequestEvent()!, 'set-cookie', setCookie)
      }

      // Extract the token data from the raw response
      const tokenData = refreshResponse._data!

      // Fetch user data with the new access token
      const user = await $fetch<User>(`${config.public.apiUrl}/auth/me`, {
        method: 'GET',
        headers: {
          cookie: cookieHeader,
          Authorization: `Bearer ${tokenData.access_token}`,
        },
      })

      // Populate the Pinia store - Pinia hydrates this to the client automatically
      // The 30-second buffer in isTokenExpired handles any server/client clock skew
      authStore.$patch({
        user,
        accessToken: tokenData.access_token,
        expiresAt: Date.now() + tokenData.expires_in * 1000,
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
