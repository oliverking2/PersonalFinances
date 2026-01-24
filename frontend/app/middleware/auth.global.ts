// =============================================================================
// Global Auth Middleware
// Runs on every route change to check authentication status
// =============================================================================
// Design decision: Client-only execution
// - SSR would require forwarding cookies from browser to API, adding complexity
// - For this app, a brief client-side auth check is acceptable
// =============================================================================

export default defineNuxtRouteMiddleware(async (to) => {
  // ---------------------------------------------------------------------------
  // Skip on server - auth runs client-side only
  // ---------------------------------------------------------------------------
  if (import.meta.server) {
    return
  }

  // ---------------------------------------------------------------------------
  // Allow public pages (login, etc.) without auth check
  // Pages mark themselves as public via: definePageMeta({ public: true })
  // ---------------------------------------------------------------------------
  if (to.meta.public) {
    return
  }

  const authStore = useAuthStore()

  // ---------------------------------------------------------------------------
  // Check if we need to refresh the session
  // This covers two cases:
  // 1. Fresh page load: user is null, expiresAt is 0 (triggers refresh)
  // 2. Token about to expire: isTokenExpired returns true
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
