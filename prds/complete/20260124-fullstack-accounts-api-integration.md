# PRD: Accounts API Integration

**Status**: Complete
**Author**: Claude
**Created**: 2026-01-24
**Updated**: 2026-01-24

---

## Overview

Replace the mock data in the frontend accounts composable with real API calls to the backend. This connects the Accounts page to live data stored in the database.

## Problem Statement

The frontend currently uses hardcoded mock data in `useAccountsApi.ts` for development. The backend already has functional endpoints for accounts, connections, and institutions. These need to be wired together so users can view their real bank connections and accounts.

## Goals

- Frontend fetches real account data from backend API
- Type contracts between frontend and backend are aligned
- Authenticated requests work correctly with token refresh
- Error states are handled gracefully

## Non-Goals

- Implementing connection creation (GoCardless OAuth flow) - separate PRD
- Implementing connection reauthorisation - separate PRD
- Changes to backend endpoints (already complete)
- UI/UX changes to the Accounts page

---

## User Stories

1. **As a** user, **I want to** see my real bank connections on the Accounts page, **so that** I can view my actual financial data.
2. **As a** user, **I want to** update my connection and account names, **so that** I can organise my accounts.
3. **As a** user, **I want to** delete a bank connection, **so that** I can remove institutions I no longer use.

---

## Proposed Solution

### High-Level Design

Create an authenticated fetch utility that encapsulates auth header injection and token refresh logic. Refactor `useAccountsApi` to use this utility instead of returning mock data.

### API Endpoints (Already Exist)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/connections` | List user's bank connections |
| GET | `/api/connections/{id}` | Get single connection |
| PATCH | `/api/connections/{id}` | Update connection friendly_name |
| DELETE | `/api/connections/{id}` | Delete connection |
| GET | `/api/accounts` | List accounts (optional connection_id filter) |
| GET | `/api/accounts/{id}` | Get single account |
| PATCH | `/api/accounts/{id}` | Update account display_name |
| GET | `/api/institutions` | List available institutions |

### Type Alignment

Frontend types need to match backend Pydantic response models:

**AccountBalance:**
```typescript
// Before
interface AccountBalance {
  amount: number
  currency: string
  as_of: string  // ❌ Backend doesn't have this
}

// After
interface AccountBalance {
  amount: number
  currency: string
  type: string  // ✅ Matches backend
}
```

**CreateConnectionResponse / ReauthoriseResponse:**
```typescript
// Before
interface CreateConnectionResponse {
  id: string
  auth_url: string  // ❌ Backend uses "link"
}

// After
interface CreateConnectionResponse {
  id: string
  link: string  // ✅ Matches backend
}
```

### Authenticated Fetch Utility

New composable `useAuthenticatedFetch.ts`:

```typescript
export function useAuthenticatedFetch() {
  const config = useRuntimeConfig()
  const authStore = useAuthStore()

  async function authFetch<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    // Refresh token if expired
    if (authStore.isTokenExpired) {
      await authStore.refreshToken()
    }

    return $fetch<T>(path, {
      baseURL: config.public.apiUrl,
      credentials: 'include',
      headers: {
        Authorization: `Bearer ${authStore.accessToken}`,
        ...options.headers,
      },
      ...options,
    })
  }

  return { authFetch }
}
```

---

## Technical Considerations

### Dependencies

- Auth store must be initialised before API calls
- Backend must be running with database populated

### Error Handling

- 401: Token expired (trigger refresh, retry)
- 404: Resource not found
- 501: Not implemented (create/reauthorise endpoints)
- Network errors: Display user-friendly message

### Security

- Access token sent via Authorization header (already established pattern)
- No secrets stored in frontend
- All requests go through authenticated endpoints

---

## Implementation Plan

### Phase 1: Type Alignment

- [x] Update `AccountBalance` interface (as_of → type)
- [x] Update `CreateConnectionResponse` (auth_url → link)
- [x] Update `ReauthoriseResponse` (auth_url → link, add id)
- [x] Add `total` to `InstitutionListResponse`
- [x] Add optional `provider` to `Institution`

### Phase 2: Authenticated Fetch

- [x] Create `useAuthenticatedFetch` composable
- [ ] Test token refresh flow

### Phase 3: API Integration

- [x] Replace `fetchConnections()` mock with real API call
- [x] Replace `fetchAccounts()` mock with real API call
- [x] Replace `fetchInstitutions()` mock with real API call
- [x] Replace `updateConnection()` mock with real API call
- [x] Replace `updateAccount()` mock with real API call
- [x] Replace `deleteConnection()` mock with real API call
- [x] Handle 501 for `createConnection()` and `reauthoriseConnection()`

### Phase 4: Testing

- [ ] Manual testing with real data
- [ ] Verify error states display correctly

---

## Testing Strategy

- [ ] Manual test: Connections load from database
- [ ] Manual test: Accounts load and group by connection
- [ ] Manual test: Update connection name persists
- [ ] Manual test: Update account display name persists
- [ ] Manual test: Delete connection removes it and accounts
- [ ] Manual test: Create connection shows "Coming soon" message
- [ ] Manual test: Reauthorise connection shows "Coming soon" message
- [x] Run `make check` in frontend directory

---

## Rollout Plan

1. **Development**: Local testing with both servers running
2. **Production**: Deploy backend first (already has endpoints), then frontend

---

## Decisions Made

- Create/reauthorise buttons will remain visible and show a "Coming soon" message when clicked (501 response from backend)

---

## References

- Frontend CLAUDE.md: Mock-first development pattern
- Backend CLAUDE.md: Two-layer data architecture
- Existing auth pattern in `stores/auth.ts`
