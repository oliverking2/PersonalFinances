# PRD: Delete Connection Endpoint

**Date:** 2026-01-24
**Scope:** backend
**Status:** Draft

## Overview

Implement a DELETE endpoint for connections that removes the connection from the local database and revokes access on GoCardless.

## Current State

### What Exists

- `Connection` model with cascade delete to `Account` → `Holding` and `Transaction`
- `delete_requisition_data_by_id()` in `src/providers/gocardless/api/requisition.py`
- API endpoint pattern for connections at `/api/connections`
- User ownership verification via `get_user_connection()` dependency

### What's Missing

- DELETE endpoint for connections
- Database operation to delete a connection
- Integration between API and GoCardless deletion

## Requirements

### 1. Delete Connection Endpoint

**Endpoint:** `DELETE /api/connections/{id}`

**Response:** `204 No Content`

**Error Responses:**

- `404 Not Found` - Connection doesn't exist or belongs to another user
- `502 Bad Gateway` - GoCardless API error (connection deleted locally, but remote deletion failed)

**Implementation:**

1. Verify connection belongs to current user (existing pattern)
2. Get the `provider_id` (requisition ID) from the connection
3. Delete the requisition on GoCardless (if provider is gocardless)
4. Delete the connection from the database (cascades to accounts, holdings, transactions)
5. Return 204

**Important:** Delete locally even if GoCardless deletion fails. The GoCardless requisition will expire naturally. Log the error and return 502 to inform the user, but don't leave orphaned local data.

### 2. Database Operation

**Location:** `src/postgres/common/operations/connections.py`

```python
def delete_connection(session: Session, connection_id: UUID) -> None:
    """Delete a connection and all associated data.

    :param session: Database session.
    :param connection_id: Connection UUID to delete.
    :raises ConnectionNotFoundError: If connection doesn't exist.
    """
    connection = session.get(Connection, connection_id)
    if not connection:
        raise ConnectionNotFoundError(connection_id)
    session.delete(connection)
    # Cascade handles accounts, holdings, transactions
```

### 3. GoCardless Deletion

The existing `delete_requisition_data_by_id()` function handles this. It:

- Calls `DELETE /api/v2/requisitions/{id}/`
- Revokes bank access immediately
- Returns confirmation

## Design Decision: Always Delete on GoCardless

For a personal finance app, when a user explicitly removes a bank connection, they expect:

1. Their data removed from the app
2. The app's access to their bank revoked

Not deleting on GoCardless would leave a "zombie" connection where the app could still technically pull data even though the user removed it. This violates the principle of least surprise.

## Edge Cases

**GoCardless requisition already deleted/expired:**

- GoCardless returns 404
- Treat as success (goal achieved)

**GoCardless API down:**

- Delete locally anyway
- Log error for debugging
- Return 502 with message about partial deletion

**Connection has no provider_id (shouldn't happen):**

- Delete locally
- Log warning

## Testing

### Unit Tests

- `test_delete_connection_success` - Happy path, 204 returned
- `test_delete_connection_not_found` - 404 for non-existent connection
- `test_delete_connection_wrong_user` - 404 for other user's connection
- `test_delete_connection_cascades` - Accounts and transactions removed

### Integration Tests (with mocked GoCardless)

- `test_delete_removes_on_gocardless` - API called with correct requisition ID
- `test_delete_succeeds_when_gocardless_404` - Already deleted, still succeeds
- `test_delete_succeeds_when_gocardless_fails` - Local deleted, 502 returned

## Files to Modify

1. `src/api/connections/endpoints.py` - Add DELETE endpoint
2. `src/postgres/common/operations/connections.py` - Add delete operation (create if needed)
3. `testing/api/connections/test_endpoints.py` - Add tests

## Out of Scope

- Soft delete / archive functionality
- Bulk delete multiple connections
- Frontend changes (already has delete button pattern)

## Success Criteria

- [ ] User can delete a connection from the API
- [ ] Associated accounts, holdings, and transactions are removed
- [ ] GoCardless requisition is deleted (bank access revoked)
- [ ] Graceful handling when GoCardless deletion fails
