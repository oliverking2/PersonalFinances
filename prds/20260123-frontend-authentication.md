# PRD: Authentication System - Frontend

**Status**: Draft
**Author**: Oli
**Created**: 2026-01-23
**Updated**: 2026-01-23
**Depends On**: `20260123-backend-authentication.md`

---

## Overview

Implement frontend authentication in Nuxt 4, integrating with the backend auth API. Manages access tokens in memory, handles automatic token refresh on 401 responses, and provides auth state to the application.

## Problem Statement

The frontend needs to authenticate users, maintain session state across the application, and handle token expiration transparently without storing sensitive tokens in persistent browser storage.

## Goals

- Login form that calls backend `/auth/login`
- Access token stored in memory only (not localStorage)
- Automatic 401 interception with token refresh retry
- Auth state available to all components via composable
- Silent re-authentication on page load
- Logout clears state and redirects

## Non-Goals

- OAuth / social login UI
- Registration flow (may be stubbed or separate PRD)
- Password reset UI
- Session management UI (view/revoke sessions)

---

## User Stories

1. **As a** user, **I want to** see a login form and enter my credentials, **so that** I can access my account
2. **As a** user, **I want to** stay logged in when I navigate between pages, **so that** I don't need to re-authenticate constantly
3. **As a** user, **I want to** remain logged in after refreshing the page, **so that** I don't lose my session
4. **As a** user, **I want to** click logout and be redirected to login, **so that** I know my session has ended

---

## Proposed Solution

### Auth Composable: `useAuth()`

Location: `app/composables/useAuth.ts`

```typescript
export function useAuth() {
  // State (module-level, persists across component instances)
  const accessToken = ref<string | null>(null)
  const user = ref<User | null>(null)
  const isAuthenticated = computed(() => !!accessToken.value)
  const isLoading = ref(false)

  // Actions
  async function login(email: string, password: string): Promise<void>
  async function logout(): Promise<void>
  async function refresh(): Promise<boolean>  // returns success
  async function fetchUser(): Promise<void>

  return {
    accessToken: readonly(accessToken),
    user: readonly(user),
    isAuthenticated,
    isLoading,
    login,
    logout,
    refresh,
    fetchUser,
  }
}
```

**Key behaviours:**

- `accessToken` is a module-level `ref`, not component state - survives component unmounts
- `login()` calls `/auth/login`, stores access token in memory, cookie set automatically by browser
- `refresh()` calls `/auth/refresh`, updates access token, returns `false` if refresh fails
- `logout()` calls `/auth/logout`, clears memory state, redirects to `/login`

### API Client with Interceptors

Location: `app/utils/api.ts` or as a Nuxt plugin

Using `ofetch` (Nuxt's built-in):

```typescript
import { ofetch } from 'ofetch'

export const api = ofetch.create({
  baseURL: useRuntimeConfig().public.apiBase,
  credentials: 'include',  // Send cookies cross-origin

  async onRequest({ options }) {
    const { accessToken } = useAuth()
    if (accessToken.value) {
      options.headers = {
        ...options.headers,
        Authorization: `Bearer ${accessToken.value}`,
      }
    }
  },

  async onResponseError({ response }) {
    if (response.status === 401) {
      const { refresh, logout } = useAuth()
      const success = await refresh()
      if (!success) {
        await logout()
        throw new Error('Session expired')
      }
      // Retry original request - ofetch doesn't auto-retry,
      // caller should handle this or we wrap in a retry utility
    }
  },
})
```

**Note:** `ofetch` doesn't have built-in retry on error. Options:
1. Wrap API calls in a utility that retries once after refresh
2. Use `ky` which has retry support
3. Handle retry at call site

Recommend option 1: a `fetchWithRetry` wrapper.

### Silent Re-auth on Page Load

Location: `app/app.vue` or `app/plugins/auth.ts`

```typescript
// In app.vue setup or a client plugin
const { refresh, isLoading } = useAuth()

onMounted(async () => {
  isLoading.value = true
  await refresh()  // Attempt to restore session from refresh cookie
  isLoading.value = false
})
```

If refresh succeeds, user is authenticated. If it fails (no cookie or expired), user stays logged out.

### Route Protection

Location: `app/middleware/auth.ts`

```typescript
export default defineNuxtRouteMiddleware((to) => {
  const { isAuthenticated, isLoading } = useAuth()

  // Wait for initial auth check
  if (isLoading.value) return

  const publicRoutes = ['/login', '/register']
  if (!isAuthenticated.value && !publicRoutes.includes(to.path)) {
    return navigateTo('/login')
  }
})
```

### Login Page

Location: `app/pages/login.vue`

- Form with email/password inputs
- Calls `login()` on submit
- Shows error message on failure
- Redirects to `/` (or stored redirect path) on success

---

## Technical Considerations

### Why Memory-Only Token Storage?

| Storage | XSS Risk | Survives Refresh | Our Choice |
|---------|----------|------------------|------------|
| localStorage | High (JS accessible) | Yes | No |
| sessionStorage | High (JS accessible) | No | No |
| Memory (ref) | Low (not persistent) | No | Yes |
| HttpOnly cookie | None (not JS accessible) | Yes | For refresh token only |

Access token in memory + refresh token in HttpOnly cookie gives us:
- XSS can't steal refresh token
- Page refresh triggers `/auth/refresh` to restore session
- Closing browser clears memory; reopening uses refresh cookie

### Configuration

`nuxt.config.ts`:
```typescript
export default defineNuxtConfig({
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000',
    },
  },
})
```

`.env`:
```
NUXT_PUBLIC_API_BASE=http://localhost:8000
```

### CORS and Credentials

The backend must have:
- `allow_credentials=True`
- Frontend origin in `allow_origins`

The frontend must have:
- `credentials: 'include'` on all fetch requests

### Error Handling

| Scenario | Handling |
|----------|----------|
| Login fails (401) | Show "Invalid email or password" |
| Login fails (429) | Show "Too many attempts, try again later" |
| Refresh fails | Redirect to login (session expired) |
| API call fails (401) | Auto-refresh + retry, or logout if refresh fails |
| Network error | Show generic error, don't logout |

---

## Implementation Plan

### Phase 1: Core Auth

- [ ] Create `useAuth` composable with state and actions
- [ ] Create `api` client with `credentials: 'include'`
- [ ] Add request interceptor for Authorization header
- [ ] Implement `login()` action
- [ ] Implement `logout()` action
- [ ] Implement `refresh()` action
- [ ] Create login page with form

### Phase 2: Session Persistence

- [ ] Add silent re-auth in app.vue or plugin
- [ ] Add loading state during initial auth check
- [ ] Create auth middleware for route protection
- [ ] Handle redirect back to original page after login

### Phase 3: Error Handling

- [ ] Add 401 response interceptor with refresh retry
- [ ] Create `fetchWithRetry` utility or handle at call sites
- [ ] Add user-facing error messages for auth failures
- [ ] Handle network errors gracefully

### Phase 4: Testing

- [ ] Unit test `useAuth` composable
- [ ] Test login flow
- [ ] Test 401 → refresh → retry flow
- [ ] Test logout clears state
- [ ] E2E test full auth journey

---

## Testing Strategy

- [ ] Unit test: `login()` stores token and sets user
- [ ] Unit test: `logout()` clears state
- [ ] Unit test: `refresh()` updates token on success, returns false on failure
- [ ] Unit test: `isAuthenticated` computed correctly reflects state
- [ ] Integration test: API client attaches Authorization header
- [ ] Integration test: 401 triggers refresh attempt
- [ ] E2E test: Login → navigate → refresh page → still authenticated
- [ ] E2E test: Login → logout → redirected to login

---

## Rollout Plan

1. **Development**: Test against local backend, verify cookie handling on localhost
2. **Staging**: Test with deployed backend, verify CORS and Secure cookies
3. **Production**: Deploy, verify auth flows in production environment

---

## Open Questions

- [ ] Use `ofetch` (built-in) or switch to `ky` for better retry support?
- [ ] Where to store intended destination for post-login redirect?
- [ ] Show "session expired" toast or just silently redirect to login?

---

## References

- [Nuxt 3 Composables](https://nuxt.com/docs/guide/directory-structure/composables)
- [ofetch documentation](https://github.com/unjs/ofetch)
