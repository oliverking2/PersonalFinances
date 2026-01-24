# PRD: Backend GoCardless OAuth Flow

**Date:** 2026-01-24
**Scope:** backend
**Status:** Draft

## Overview

Implement the backend endpoints for the GoCardless OAuth flow, enabling users to connect their bank accounts. Also create a database seed script for development.

## Current State

### What Exists

- GoCardless API client with token management and retry logic (`src/providers/gocardless/api/core.py`)
- Requisition creation function `create_new_requisition_link()` (`src/postgres/gocardless/operations/requisitions.py`)
- Database models for requisitions, bank accounts, balances, transactions
- Status mapping from GoCardless statuses to normalized ConnectionStatus
- Dagster sync pipeline that updates connection/account statuses
- Connection model with `user_id` FK (permission layer already exists)
- API endpoints that return 501: `POST /api/connections`, `POST /api/connections/{id}/reauthorise`

### What's Missing

1. Implementation of create connection endpoint
2. OAuth callback endpoint
3. Implementation of reauthorise endpoint
4. Database seed script for development

## Requirements

### 1. Create Connection Endpoint

**Endpoint:** `POST /api/connections`

**Request:**

```json
{
  "institution_id": "NATIONWIDE_NAIAGB21",
  "friendly_name": "My Nationwide Account"
}
```

**Response:**

```json
{
  "id": "uuid-of-connection",
  "link": "https://ob.gocardless.com/psd2/start/..."
}
```

**Implementation:**

1. Validate institution exists via `GET /api/institutions/{id}` or lookup
2. Call `create_new_requisition_link(session, institution_id, friendly_name)`
3. Create a Connection record with:
   - `user_id` = current authenticated user
   - `provider` = "gocardless"
   - `provider_id` = requisition ID from GoCardless
   - `institution_id` = institution UUID
   - `friendly_name` = from request
   - `status` = PENDING
4. Return the connection ID and the OAuth link from the requisition

### 2. OAuth Callback Endpoint

**Endpoint:** `GET /api/connections/callback`

**Query Parameters:**

- `ref` - The requisition reference (UUID we sent to GoCardless)

**Behaviour:**

1. Look up the RequisitionLink by reference
2. Fetch latest status from GoCardless API
3. Update requisition status in database
4. Update corresponding Connection status
5. If status is "LN" (linked), fetch and store bank accounts
6. Redirect to frontend: `{FRONTEND_URL}/accounts?callback=success` or `?callback=error&reason=...`

**Notes:**

- This endpoint does NOT require authentication (user is returning from external redirect)
- The `ref` parameter ties back to the user's connection
- Frontend URL should be configurable via environment variable

### 3. Reauthorise Connection Endpoint

**Endpoint:** `POST /api/connections/{id}/reauthorise`

**Response:**

```json
{
  "id": "uuid-of-connection",
  "link": "https://ob.gocardless.com/psd2/start/..."
}
```

**Implementation:**

1. Verify connection belongs to current user (existing pattern)
2. Verify connection status is EXPIRED
3. Create new requisition for same institution
4. Update connection's `provider_id` to new requisition ID
5. Set connection status back to PENDING
6. Return the new OAuth link

### 4. Database Seed Script

**Location:** `backend/scripts/seed_dev_user.py`

**Purpose:** Create a development user and associate existing GoCardless data with them.

**Functionality:**

```python
# Usage: poetry run python scripts/seed_dev_user.py

# 1. Create user (if not exists)
#    - username: "dev"
#    - password: "devpassword123"
#    - first_name: "Dev"
#    - last_name: "User"

# 2. For each existing RequisitionLink without a Connection:
#    - Look up or create Institution from requisition's institution_id
#    - Create Connection linking requisition to user
#    - Sync accounts from gc_bank_accounts to accounts table

# 3. Print summary of what was created/linked
```

**Why this approach:**

- Existing `backend/src/postgres/gocardless/seed.py` already pulls raw data from GoCardless API
- This new script creates the user layer on top of that data
- Allows testing the full flow with real bank data

## Environment Variables

Existing (already in `.env_example`):

- `GC_SECRET_ID` - GoCardless API secret ID
- `GC_SECRET_KEY` - GoCardless API secret key
- `GC_CALLBACK_URL` - Callback URL (e.g., `http://localhost:8000/api/connections/callback`)

New:

- `FRONTEND_URL` - Frontend base URL for redirects (e.g., `http://localhost:3000`)

## Database Changes

None required - the schema already supports this:

- `connections.user_id` FK exists
- `connections.provider_id` can store requisition ID
- All necessary indexes exist

## Testing

### Unit Tests

- `test_create_connection_success` - Happy path
- `test_create_connection_invalid_institution` - 404 for bad institution
- `test_create_connection_unauthenticated` - 401 without token

### Integration Tests (with mocked GoCardless)

- `test_callback_success` - Status updates correctly
- `test_callback_invalid_ref` - 404 for unknown reference
- `test_reauthorise_success` - New link generated
- `test_reauthorise_not_expired` - 400 if connection not expired
- `test_reauthorise_wrong_user` - 404 for other user's connection

## Implementation Order

1. Seed script (enables testing with real data)
2. Create connection endpoint
3. Callback endpoint
4. Reauthorise endpoint
5. Tests

## Out of Scope

- End user agreement creation (noted as not possible with current GoCardless config)
- Webhook handling (using redirect-based flow)
- Automatic polling for status (Dagster handles this)

## Success Criteria

- [ ] User can initiate bank connection from frontend
- [ ] User is redirected to GoCardless, completes auth, returns to app
- [ ] Connection and accounts appear in user's account list
- [ ] Expired connections can be reauthorised
- [ ] Dev seed script creates user with linked accounts
