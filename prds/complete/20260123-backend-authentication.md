# PRD: Authentication System - Backend

**Status**: Draft
**Author**: Oli
**Created**: 2026-01-23
**Updated**: 2026-01-23

---

## Overview

Implement the backend authentication API using FastAPI with JWT access tokens and refresh token cookies. This provides the foundation that the frontend will integrate with.

## Problem Statement

The application needs secure authentication endpoints that issue short-lived JWTs for API access and manage refresh tokens server-side with rotation and replay detection.

## Goals

- Secure credential verification with password hashing
- JWT access token issuance (short-lived, stateless validation)
- Refresh token management with HttpOnly cookies
- Token rotation on every refresh
- Replay detection to prevent token theft
- Rate limiting on auth endpoints

## Non-Goals

- OAuth / external identity providers
- Multi-tenancy
- RBAC / permissions
- MFA
- Passwordless login
- Email delivery (reset/verify emails may be stubbed)
- Frontend implementation (separate PRD)

---

## User Stories

1. **As a** frontend client, **I want to** submit credentials and receive an access token, **so that** I can make authenticated API calls
2. **As a** frontend client, **I want to** exchange my refresh cookie for a new access token, **so that** sessions persist without re-entering credentials
3. **As a** frontend client, **I want to** logout and have my refresh token revoked, **so that** the session cannot be resumed

---

## Proposed Solution

### API Endpoints

| Method  | Path          | Auth Required  | Description                                                 |
|---------|---------------|----------------|-------------------------------------------------------------|
| POST    | /auth/login   | No             | Verify credentials, return access token, set refresh cookie |
| POST    | /auth/refresh | Refresh cookie | Rotate refresh token, return new access token               |
| POST    | /auth/logout  | Refresh cookie | Revoke refresh token, clear cookie                          |
| GET     | /auth/me      | Access token   | Return authenticated user info                              |

### Data Model

```sql
-- Users table (if not exists)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Refresh tokens table
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    rotated_from UUID REFERENCES refresh_tokens(id),
    user_agent TEXT,
    ip_address INET
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at) WHERE revoked_at IS NULL;
```

### Endpoint Specifications

**POST /auth/login**

Request:

```json
{
  "email": "user@example.com",
  "password": "plaintext"
}
```

Response (200):

```json
{
  "access_token": "<jwt>",
  "expires_in": 900
}
```

Response headers:

```
Set-Cookie: refresh_token=<token>; HttpOnly; Secure; SameSite=Lax; Path=/auth; Max-Age=2592000
```

Errors:

- 401: Invalid credentials
- 429: Rate limited

**POST /auth/refresh**

Request: No body (refresh token from cookie)

Response (200):

```json
{
  "access_token": "<jwt>",
  "expires_in": 900
}
```

Response headers: New refresh token cookie (rotation)

Errors:

- 401: Invalid/expired/revoked refresh token
- 401 + revoke chain: Replay detected

**POST /auth/logout**

Request: No body (refresh token from cookie)

Response (200):

```json
{
  "ok": true
}
```

Response headers:

```
Set-Cookie: refresh_token=; HttpOnly; Secure; SameSite=Lax; Path=/auth; Max-Age=0
```

**GET /auth/me**

Request headers: `Authorization: Bearer <access_token>`

Response (200):

```json
{
  "id": "uuid",
  "email": "user@example.com"
}
```

Errors:

- 401: Missing/invalid/expired access token

### Token Specifications

**Access Token (JWT):**

```json
{
  "sub": "<user_id>",
  "iat": 1234567890,
  "exp": 1234568790
}
```

- Algorithm: HS256 (symmetric, simpler) or RS256 (asymmetric, allows public verification)
- Expiry: 15 minutes
- Signed with `JWT_SECRET` from environment

**Refresh Token:**

- Format: 32 bytes of `secrets.token_urlsafe()` (256 bits entropy)
- Stored: bcrypt hash in database
- Expiry: 30 days

### Refresh Token Rotation

On every `/auth/refresh`:

1. Validate incoming token against DB (hash comparison)
2. Check not revoked and not expired
3. Mark old token as revoked (`revoked_at = now()`)
4. Generate new token, store hash with `rotated_from` pointing to old token
5. Return new access token + set new cookie

### Replay Detection

If a refresh token is presented that was already rotated (exists in DB but `revoked_at` is set):

1. Find the token chain via `rotated_from` links
2. Revoke ALL tokens in the chain (entire session compromised)
3. Return 401
4. Log security event with user_id, IP, user_agent

---

## Technical Considerations

### Dependencies

```
python-jose[cryptography]  # JWT encoding/decoding
passlib[bcrypt]            # Password hashing
```

### Configuration

Environment variables:

```
JWT_SECRET=<random-64-chars>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
```

### Cookie Configuration

```python
def get_cookie_settings() -> dict:
    is_local = settings.ENVIRONMENT == "local"
    return {
        "key": "refresh_token",
        "httponly": True,
        "secure": not is_local,  # False only for localhost
        "samesite": "lax",
        "path": "/auth",
        "max_age": 60 * 60 * 24 * 30,  # 30 days
    }
```

For local development: browsers allow non-`Secure` cookies on `localhost`.

### CORS Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],  # e.g., "http://localhost:3000"
    allow_credentials=True,  # Required for cookies
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### Rate Limiting

Apply to auth endpoints:

- `/auth/login`: 5 attempts per minute per IP
- `/auth/refresh`: 10 attempts per minute per IP

Consider `slowapi` or custom middleware.

### Security Logging

Log these events (structured logging):

- Login success: user_id, IP, user_agent
- Login failure: email (not password), IP, user_agent
- Refresh success: user_id
- Refresh replay detected: user_id, IP, user_agent (security alert)
- Logout: user_id

---

## Implementation Plan

### Phase 1: Core Auth

- [ ] Add JWT_SECRET and related config to settings
- [ ] Create Alembic migration for users table (if needed)
- [ ] Create Alembic migration for refresh_tokens table
- [ ] Implement password hashing utility (bcrypt)
- [ ] Implement JWT encode/decode utility
- [ ] Implement refresh token generation and hashing
- [ ] Create `/auth/login` endpoint
- [ ] Create `/auth/refresh` endpoint with rotation
- [ ] Create `/auth/logout` endpoint
- [ ] Create `/auth/me` endpoint
- [ ] Add `get_current_user` dependency for protected routes

### Phase 2: Security

- [ ] Implement replay detection in `/auth/refresh`
- [ ] Add rate limiting middleware
- [ ] Add security event logging
- [ ] Create cleanup job for expired tokens (Dagster asset or cron)

### Phase 3: Testing

- [ ] Unit tests: password hashing, JWT encode/decode
- [ ] Unit tests: refresh token rotation logic
- [ ] Integration tests: full auth flows
- [ ] Integration tests: replay detection
- [ ] Integration tests: rate limiting

---

## Testing Strategy

- [ ] Unit test: `hash_password` and `verify_password`
- [ ] Unit test: `create_access_token` and `decode_access_token`
- [ ] Unit test: refresh token generation and hash verification
- [ ] Integration test: login with valid credentials returns tokens
- [ ] Integration test: login with invalid credentials returns 401
- [ ] Integration test: refresh rotates token and returns new access token
- [ ] Integration test: using old refresh token after rotation triggers replay detection
- [ ] Integration test: logout revokes token and clears cookie
- [ ] Integration test: `/auth/me` returns user with valid token, 401 without

---

## Rollout Plan

1. **Development**: Test with `ENVIRONMENT=local`, cookies on localhost
2. **Staging**: Test with HTTPS, verify cookie `Secure` flag works
3. **Production**: Deploy, monitor auth logs for anomalies

---

## Open Questions

- [ ] HS256 vs RS256? Recommend HS256 for simplicity unless we need public key verification
- [ ] Use `slowapi` for rate limiting or custom middleware?
- [ ] Store refresh tokens in Redis for faster lookups? (Postgres is fine to start)

---

## References

- [FastAPI Security docs](https://fastapi.tiangolo.com/tutorial/security/)
- [python-jose](https://python-jose.readthedocs.io/)
