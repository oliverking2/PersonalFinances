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

    // DEBUG: Log incoming cookies
    console.log('[SSR Auth] ====== SSR Auth Check ======')
    console.log('[SSR Auth] Route:', to.path)
    console.log(
      '[SSR Auth] All cookies from browser:',
      cookieHeader || '(none)',
    )
    console.log('[SSR Auth] API URL:', config.public.apiUrl)

    // Check if we have the refresh_token cookie
    // In local dev, cookie won't be sent because frontend (port 3000) and backend (port 8000)
    // are different origins. In production, COOKIE_DOMAIN must be set to share across subdomains.
    const hasRefreshToken = cookieHeader?.includes('refresh_token=') ?? false
    console.log('[SSR Auth] Has refresh_token:', hasRefreshToken)

    if (!cookieHeader || !hasRefreshToken) {
      if (import.meta.dev) {
        console.log(
          '[SSR Auth] Dev mode, skipping SSR auth - will use client-side',
        )
        return
      }
      console.log('[SSR Auth] No refresh_token cookie, redirecting to login')
      return navigateTo('/login')
    }

    // At this point TypeScript knows cookieHeader is a string (not undefined)
    try {
      // Call /auth/refresh with the cookie forwarded
      console.log('[SSR Auth] Calling backend /auth/refresh...')
      const refreshResponse = await $fetch.raw<RefreshResponse>(
        `${config.public.apiUrl}/auth/refresh`,
        {
          method: 'POST',
          headers: {
            cookie: cookieHeader,
          },
        },
      )

      console.log(
        '[SSR Auth] Refresh succeeded, status:',
        refreshResponse.status,
      )

      // Forward the Set-Cookie header from backend to browser
      // This is critical because backend rotates the refresh token on each refresh
      const setCookie = refreshResponse.headers.get('set-cookie')
      console.log('[SSR Auth] Set-Cookie from backend:', setCookie || '(none)')

      if (setCookie) {
        appendResponseHeader(useRequestEvent()!, 'set-cookie', setCookie)
        console.log('[SSR Auth] Forwarded Set-Cookie to browser response')
      } else {
        console.log('[SSR Auth] WARNING: No Set-Cookie header from backend!')
      }

      // Extract the token data from the raw response
      const tokenData = refreshResponse._data!
      console.log(
        '[SSR Auth] Got access token, expires_in:',
        tokenData.expires_in,
      )

      // Fetch user data with the new access token
      const user = await $fetch<User>(`${config.public.apiUrl}/auth/me`, {
        method: 'GET',
        headers: {
          cookie: cookieHeader,
          Authorization: `Bearer ${tokenData.access_token}`,
        },
      })

      console.log('[SSR Auth] Got user:', user.username)

      // Populate the Pinia store - Pinia hydrates this to the client automatically
      authStore.$patch({
        user,
        accessToken: tokenData.access_token,
        expiresAt: Date.now() + tokenData.expires_in * 1000,
      })

      console.log('[SSR Auth] Store hydrated, auth complete')
    } catch (error) {
      // Refresh failed - cookie invalid, expired, or backend unreachable
      console.error('[SSR Auth] Refresh failed:', error)
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
