# Authentication API

Complete API contract for frontend authentication implementation.

## Overview

The authentication system uses:

- **JWT access tokens** (15 min expiry) - sent in `Authorization: Bearer <token>` header
- **Refresh tokens** (30 day expiry) - stored in HttpOnly cookies, rotated on each use

### Authentication Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AUTHENTICATION FLOW                               │
└─────────────────────────────────────────────────────────────────────────────┘

1. LOGIN
   User submits username/password
   ┌─────────┐     POST /auth/login      ┌─────────┐
   │ Frontend│ ─────────────────────────▶│ Backend │
   │         │                           │         │
   │         │◀───────────────────────── │         │
   └─────────┘  { access_token, ... }    └─────────┘
               + Set-Cookie: refresh_token (HttpOnly)

2. AUTHENTICATED REQUESTS
   Frontend stores access_token in memory (NOT localStorage)
   ┌─────────┐  GET /auth/me + Bearer    ┌─────────┐
   │ Frontend│ ─────────────────────────▶│ Backend │
   │         │◀───────────────────────── │         │
   └─────────┘      { user data }        └─────────┘

3. TOKEN REFRESH (when access_token expires)
   Cookie sent automatically by browser
   ┌─────────┐   POST /auth/refresh      ┌─────────┐
   │ Frontend│ ─────────────────────────▶│ Backend │
   │         │                           │         │
   │         │◀───────────────────────── │         │
   └─────────┘  { new access_token }     └─────────┘
               + Set-Cookie: new refresh_token

4. LOGOUT
   ┌─────────┐    POST /auth/logout      ┌─────────┐
   │ Frontend│ ─────────────────────────▶│ Backend │
   │         │◀───────────────────────── │         │
   └─────────┘       { ok: true }        └─────────┘
               + Clear-Cookie: refresh_token
```

---

## Endpoints

### POST /auth/login

Authenticate user with username and password.

**Request:**

```http
POST /auth/login
Content-Type: application/json

{
  "username": "myuser",
  "password": "secretpassword"
}
```

| Field    | Type   | Required | Notes                           |
|----------|--------|----------|---------------------------------|
| username | string | Yes      | Case-insensitive                |
| password | string | Yes      | Min length not enforced (MVP)   |

**Success Response (200):**

```http
HTTP/1.1 200 OK
Content-Type: application/json
Set-Cookie: refresh_token=<token>; HttpOnly; Secure; SameSite=Lax; Path=/auth; Max-Age=2592000

{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 900
}
```

| Field        | Type   | Description                              |
|--------------|--------|------------------------------------------|
| access_token | string | JWT for Authorization header             |
| expires_in   | int    | Token lifetime in seconds (900 = 15 min) |

**Error Response (401):**

```json
{
  "detail": "Invalid credentials"
}
```

**Notes:**

- Same error for wrong username or wrong password (prevents enumeration)
- `Secure` flag is omitted in local development (localhost)

---

### POST /auth/register

Create a new user account.

**Request:**

```http
POST /auth/register
Content-Type: application/json

{
  "username": "newuser",
  "password": "securepassword123"
}
```

| Field    | Type   | Required | Validation                        |
|----------|--------|----------|-----------------------------------|
| username | string | Yes      | 3-50 characters, case-insensitive |
| password | string | Yes      | Minimum 8 characters              |

**Success Response (200):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "newuser"
}
```

**Error Responses:**

| Status | Detail                  | Cause                     |
|--------|-------------------------|---------------------------|
| 409    | Username already exists | Duplicate username        |
| 422    | Validation error        | Username/password invalid |

---

### POST /auth/refresh

Exchange refresh token for new access token. Performs token rotation.

**Request:**

```http
POST /auth/refresh
Cookie: refresh_token=<current_token>
```

No request body required. The refresh token is read from the HttpOnly cookie.

**Success Response (200):**

```http
HTTP/1.1 200 OK
Content-Type: application/json
Set-Cookie: refresh_token=<new_token>; HttpOnly; Secure; SameSite=Lax; Path=/auth; Max-Age=2592000

{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 900
}
```

**Error Responses:**

| Status | Detail                   | Cause                              |
|--------|--------------------------|------------------------------------|
| 401    | Refresh token required   | No cookie present                  |
| 401    | Invalid refresh token    | Token not found in database        |
| 401    | Refresh token expired    | Token past expiry date             |
| 401    | Token has been revoked   | Replay attack detected (see below) |

**Token Rotation & Replay Detection:**

- Each refresh issues a NEW refresh token and revokes the old one
- If a revoked token is reused (replay attack), ALL tokens for that user are revoked
- User must log in again after replay detection

---

### POST /auth/logout

Revoke refresh token and clear cookie.

**Request:**

```http
POST /auth/logout
Cookie: refresh_token=<token>
```

**Success Response (200):**

```http
HTTP/1.1 200 OK
Content-Type: application/json
Set-Cookie: refresh_token=; HttpOnly; Secure; SameSite=Lax; Path=/auth; Max-Age=0

{
  "ok": true
}
```

**Notes:**

- Always returns 200, even if token was invalid or missing
- Cookie is always cleared regardless of token validity

---

### GET /auth/me

Get current authenticated user's information.

**Request:**

```http
GET /auth/me
Authorization: Bearer <access_token>
```

**Success Response (200):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "myuser"
}
```

| Field    | Type   | Description           |
|----------|--------|-----------------------|
| id       | string | UUID of the user      |
| username | string | User's username       |

**Error Responses:**

| Status | Detail                    | Cause                    |
|--------|---------------------------|--------------------------|
| 401    | Not authenticated         | No Authorization header  |
| 401    | Invalid or expired token  | JWT invalid or expired   |

---

## Frontend Implementation Guide

### Token Storage

| Token Type    | Storage Location | Why                                           |
|---------------|------------------|-----------------------------------------------|
| Access token  | Memory (JS var)  | Short-lived, XSS can't persist it             |
| Refresh token | HttpOnly cookie  | JS can't access it, sent automatically        |

**Do NOT store access tokens in:**

- localStorage (XSS vulnerable, persists across sessions)
- sessionStorage (XSS vulnerable)
- Non-HttpOnly cookies (XSS vulnerable)

### Recommended State Structure

```typescript
interface AuthState {
  user: { id: string; username: string } | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}
```

### API Client Setup

```typescript
// Pseudocode for fetch wrapper
async function authFetch(url: string, options: RequestInit = {}) {
  const response = await fetch(url, {
    ...options,
    credentials: 'include', // IMPORTANT: sends cookies
    headers: {
      ...options.headers,
      'Content-Type': 'application/json',
      ...(accessToken && { Authorization: `Bearer ${accessToken}` }),
    },
  });

  // Handle 401 - try refresh
  if (response.status === 401 && !url.includes('/auth/refresh')) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      // Retry original request with new token
      return authFetch(url, options);
    }
    // Refresh failed - redirect to login
    redirectToLogin();
  }

  return response;
}
```

### Refresh Token Flow

```typescript
async function tryRefresh(): Promise<boolean> {
  try {
    const response = await fetch('/auth/refresh', {
      method: 'POST',
      credentials: 'include', // sends refresh_token cookie
    });

    if (response.ok) {
      const data = await response.json();
      accessToken = data.access_token; // Update in-memory token
      return true;
    }
    return false;
  } catch {
    return false;
  }
}
```

### App Initialisation

On app load, check if user is authenticated:

```typescript
async function initAuth() {
  // Try to refresh - if cookie exists, this will work
  const refreshed = await tryRefresh();

  if (refreshed) {
    // Fetch user info
    const response = await authFetch('/auth/me');
    if (response.ok) {
      user = await response.json();
      isAuthenticated = true;
    }
  }

  isLoading = false;
}
```

### Proactive Token Refresh

Refresh before expiry to avoid failed requests:

```typescript
function scheduleRefresh(expiresIn: number) {
  // Refresh 1 minute before expiry
  const refreshIn = (expiresIn - 60) * 1000;

  setTimeout(async () => {
    const success = await tryRefresh();
    if (success) {
      scheduleRefresh(900); // Schedule next refresh
    }
  }, refreshIn);
}
```

---

## Error Handling Summary

| Scenario                | HTTP Status | Action                              |
|-------------------------|-------------|-------------------------------------|
| Wrong credentials       | 401         | Show error, stay on login           |
| Access token expired    | 401         | Try refresh, retry request          |
| Refresh token expired   | 401         | Clear state, redirect to login      |
| Replay attack detected  | 401         | Clear state, redirect to login      |
| Network error           | -           | Show error, allow retry             |

---

## CORS Configuration

The backend allows:

- Origin: `http://localhost:3000` (frontend dev server)
- Credentials: `true` (required for cookies)
- Methods: `GET, POST, PUT, DELETE, OPTIONS`
- Headers: `Authorization, Content-Type`

Frontend requests must include `credentials: 'include'` for cookies to work.

---

## Security Notes

1. **CSRF Protection**: SameSite=Lax cookies + requiring POST for state changes
2. **XSS Mitigation**: HttpOnly cookies for refresh tokens, access tokens in memory only
3. **Replay Detection**: Token rotation with chain revocation on reuse
4. **Timing Attacks**: Same error message for invalid username vs password

---

## Testing Checklist

Before considering auth complete, verify:

- [x] Login with valid credentials shows user info
- [x] Login with wrong password shows error
- [x] Login with non-existent username shows same error
- [x] Protected route redirects to login when not authenticated
- [x] Access token refresh happens automatically before expiry
- [x] Logout clears state and redirects to login
- [x] Refreshing browser maintains session (cookie persists)
- [x] Opening new tab maintains session (shared cookie)
- [x] After logout, back button doesn't show protected content
