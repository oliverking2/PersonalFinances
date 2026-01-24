# PRD: Frontend GoCardless OAuth Callback

**Date:** 2026-01-24
**Scope:** frontend
**Status:** Draft

## Overview

Handle the return from GoCardless OAuth flow in the frontend, providing feedback to users about their connection status.

## Current State

### What Exists

- Complete UI for bank connection management (`pages/accounts.vue`)
- Modal for creating connections with institution selection (`CreateConnectionModal.vue`)
- Connection and account display components
- Redirect to GoCardless OAuth: `window.location.href = authUrl`
- API composables wired to backend endpoints

### What's Missing

- No handling of the return from GoCardless
- No feedback to user after OAuth completion
- No error handling for failed/cancelled OAuth

## Requirements

### 1. Update Accounts Page Query Parameter Handling

**Location:** `frontend/app/pages/accounts.vue`

The backend callback will redirect to `/accounts?callback=success` or `/accounts?callback=error&reason=...`

**On Page Load:**

1. Check for `callback` query parameter
2. If `callback=success`:
   - Show success toast: "Bank account connected successfully"
   - Refresh connections list
   - Clear query parameters from URL
3. If `callback=error`:
   - Show error toast with reason
   - Clear query parameters from URL
4. If no callback parameter, normal page load

**Implementation:**

```typescript
// In accounts.vue setup or onMounted
const route = useRoute()
const router = useRouter()

onMounted(async () => {
  const callback = route.query.callback as string | undefined

  if (callback === 'success') {
    toast.success('Bank account connected successfully')
    await refreshConnections()
    router.replace({ query: {} }) // Clear query params
  } else if (callback === 'error') {
    const reason = route.query.reason as string || 'Unknown error'
    toast.error(`Failed to connect bank: ${reason}`)
    router.replace({ query: {} })
  }

  // Normal data fetching...
})
```

### 2. Add Toast Notification System

If not already present, add a toast/notification system for user feedback.

**Options:**

- Vue Toastification (recommended - lightweight)
- Nuxt UI notifications (if using Nuxt UI)
- Custom toast component

**Usage Pattern:**

```typescript
const toast = useToast()
toast.success('Message')
toast.error('Error message')
```

### 3. Loading State During OAuth

**Enhancement:** Show a pending state while user is away at GoCardless.

#### Option A: LocalStorage Flag

```typescript
// Before redirect
localStorage.setItem('oauth_pending', 'true')
window.location.href = authUrl

// On return (accounts.vue onMounted)
if (localStorage.getItem('oauth_pending')) {
  localStorage.removeItem('oauth_pending')
  // Show "Checking connection status..." briefly
}
```

**Option B: Just handle the callback params** (simpler, recommended for MVP)

### 4. Handle Edge Cases

**User closes browser during OAuth:**

- Connection stays in PENDING state
- Dagster job will eventually update status
- No special handling needed

**User cancels at bank:**

- GoCardless redirects back with error
- Backend callback handles and redirects to frontend with `?callback=error&reason=cancelled`

**Network error on callback:**

- Backend should handle gracefully
- Frontend shows generic error message

## UI/UX Flow

```
1. User clicks "New Connection"
2. Modal opens, user selects bank + enters name
3. User clicks "Connect"
4. Frontend calls POST /api/connections
5. Backend returns { id, link }
6. Frontend redirects: window.location.href = link
7. User authenticates at bank (external)
8. GoCardless redirects to backend callback
9. Backend processes, redirects to /accounts?callback=success
10. Frontend shows success toast, refreshes list
11. New connection appears with accounts
```

## Testing

### Manual Testing Checklist

- [ ] Success callback shows toast and refreshes
- [ ] Error callback shows error message
- [ ] Query params are cleared after handling
- [ ] Page works normally without callback params
- [ ] Reauthorise flow works the same way

### Unit Tests

- `test_handles_success_callback` - Toast shown, data refreshed
- `test_handles_error_callback` - Error toast with reason
- `test_clears_query_params` - URL cleaned up
- `test_normal_load_without_callback` - No side effects

## Files to Modify

1. `frontend/app/pages/accounts.vue` - Add callback handling
2. `frontend/app/plugins/toast.ts` or similar - Add toast plugin (if needed)
3. `frontend/nuxt.config.ts` - Register toast plugin (if needed)

## Dependencies

- Backend PRD must be implemented first (callback endpoint)
- Toast library installation (if not present)

## Out of Scope

- Dedicated callback route (using query params on existing page instead)
- Progress indicator during OAuth (user is on external site)
- Retry mechanism for failed connections (user can try again manually)

## Success Criteria

- [ ] User sees success message after connecting bank
- [ ] User sees error message if connection fails
- [ ] Connections list updates automatically after success
- [ ] URL is clean after callback handling
