// =============================================================================
// Auth Store
// Manages authentication state: user, tokens, login/logout/refresh
// =============================================================================

import { defineStore } from 'pinia'

// -----------------------------------------------------------------------------
// Types for API responses
// -----------------------------------------------------------------------------

interface User {
  id: string
  username: string
  first_name: string // TODO: Backend will add these fields
  last_name: string
}

interface LoginResponse {
  access_token: string
  expires_in: number // seconds until token expires
}

interface RefreshResponse {
  access_token: string
  expires_in: number
}

interface LogoutResponse {
  ok: boolean
}

type MeResponse = User

// =============================================================================
// Store Definition
// =============================================================================

export const useAuthStore = defineStore('auth', () => {
  const config = useRuntimeConfig()

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  const user = ref<User | null>(null)
  const loading = ref(false)
  const accessToken = ref('')
  const expiresAt = ref(0) // timestamp (ms) when token expires

  // ---------------------------------------------------------------------------
  // Getters
  // ---------------------------------------------------------------------------

  // User is authenticated if we have user data
  const isAuthenticated = computed(() => user.value !== null)

  // Display name: "First Last" or fallback to username if names not set
  const displayName = computed(() => {
    if (!user.value) return ''
    const { first_name, last_name, username } = user.value
    if (first_name && last_name) return `${first_name} ${last_name}`
    if (first_name) return first_name
    return username
  })

  // Token is "expired" if we're within 30 seconds of expiry
  // This gives us a buffer to refresh before the token actually expires
  // Also returns true when expiresAt is 0 (fresh page load with no token)
  const isTokenExpired = computed(() => expiresAt.value - 30000 < Date.now())

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------

  // Clear all auth state - used on logout or when refresh fails
  function resetState() {
    user.value = null
    accessToken.value = ''
    expiresAt.value = 0
  }

  // Login with username and password
  // - Calls /auth/login to get access token (also sets refresh cookie)
  // - Then fetches user data from /auth/me
  async function login(username: string, password: string) {
    try {
      loading.value = true

      // Get access token - server also sets HttpOnly refresh cookie
      const response = await $fetch<LoginResponse>(
        `${config.public.apiUrl}/auth/login`,
        {
          method: 'POST',
          credentials: 'include', // needed to receive the cookie
          body: { username, password },
        },
      )

      // Store token and calculate expiry timestamp
      accessToken.value = response.access_token
      expiresAt.value = Date.now() + response.expires_in * 1000

      // Fetch user data with the new token
      user.value = await $fetch<MeResponse>(`${config.public.apiUrl}/auth/me`, {
        method: 'GET',
        credentials: 'include',
        headers: { Authorization: `Bearer ${accessToken.value}` },
      })
    } catch (error) {
      console.error('Login failed:', error)
      resetState()
      throw error
    } finally {
      loading.value = false
    }
  }

  // Logout - clears local state immediately, then revokes token on server
  // Optimistic: user sees instant logout, API call happens in background
  async function logout() {
    // Clear local state first for instant feedback
    resetState()

    // Then revoke token on server (fire and forget from caller's perspective)
    try {
      await $fetch<LogoutResponse>(`${config.public.apiUrl}/auth/logout`, {
        method: 'POST',
        credentials: 'include', // sends refresh cookie for revocation
      })
    } catch (error) {
      // Log but don't throw - user is already logged out locally
      // Orphaned server token will expire on its own
      console.error('Logout API call failed:', error)
    }
  }

  // Refresh the access token using the HttpOnly refresh cookie
  // - Called by middleware when token is expired or on fresh page load
  // - Also fetches user data since we need it after page refresh
  async function refreshToken() {
    try {
      // Get new access token - browser sends refresh cookie automatically
      const response = await $fetch<RefreshResponse>(
        `${config.public.apiUrl}/auth/refresh`,
        {
          method: 'POST',
          credentials: 'include',
        },
      )

      accessToken.value = response.access_token
      expiresAt.value = Date.now() + response.expires_in * 1000

      // Fetch user data - needed because store is empty after page refresh
      user.value = await $fetch<MeResponse>(`${config.public.apiUrl}/auth/me`, {
        method: 'GET',
        credentials: 'include',
        headers: { Authorization: `Bearer ${accessToken.value}` },
      })
    } catch (error) {
      console.error('Token refresh failed:', error)
      resetState()
      throw error
    }
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    // State
    user,
    loading,
    accessToken,
    expiresAt, // Exposed for SSR hydration in auth middleware

    // Getters
    isAuthenticated,
    isTokenExpired,
    displayName,

    // Actions
    login,
    logout,
    refreshToken,
  }
})
