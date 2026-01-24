# PRD: Backend Code Quality Improvements

**Status**: Complete
**Author**: Claude
**Created**: 2026-01-17
**Updated**: 2026-01-24

---

## Overview

Address code quality issues identified during codebase review: generic exception handling, session management, currency precision, retry logic, and sensitive data in logs.

## Problem Statement

Several code patterns make the codebase harder to maintain and debug:

1. Generic `except Exception: raise` patterns that obscure stack traces
2. Database sessions created without proper cleanup
3. Currency stored as `float` causing precision loss
4. No retry logic for transient network failures
5. Database passwords logged in plain text

## Goals

- Remove anti-patterns that obscure errors
- Standardise database session lifecycle
- Fix data type issues for currency
- Add resilience for network operations
- Prevent sensitive data leakage in logs

## Non-Goals

- Major refactoring beyond quality fixes
- Adding new features
- Changing database schema (except currency precision)

---

## Improvements

### 1. Remove Generic Exception Anti-patterns

**Affected files**: `src/aws/ssm_parameters.py`, `src/postgres/gocardless/operations/bank_accounts.py`

**Issue**: Catching and immediately re-raising adds no value and obscures stack traces.

**Fix**: Remove unnecessary try-except blocks or add meaningful error context.

**Status**: [x] Complete

### 2. Standardise Database Session Management

**File**: `src/postgres/core.py`

**Issue**: Sessions created without cleanup, causing potential connection leaks.

**Fix**:

- Add context manager pattern for session lifecycle (`session_scope()`)
- Configure connection pooling explicitly via `get_engine()`
- Cache engines with `lru_cache` to reuse connections

**Status**: [x] Complete

### 3. Fix Currency Precision

**File**: `src/postgres/gocardless/models.py`

**Issue**: `balance_amount` uses `float` which causes precision loss for currency.

**Fix**: Use `Numeric` type with explicit precision for all money fields.

**Status**: [x] Already implemented - uses `Numeric(12, 2)`

### 4. Add Request Retry Logic

**File**: `src/providers/gocardless/api/core.py`

**Issue**: No retry logic for transient failures (network glitches, 5xx errors).

**Fix**: Implemented exponential backoff with `tenacity`:

- Retries on connection errors, timeouts, and 5xx responses
- Uses exponential backoff (1-10 seconds)
- Maximum 3 attempts before failing
- Does not retry 4xx client errors
- Uses `requests.Session` for connection pooling

**Status**: [x] Complete

### 5. Mask Sensitive Data in Logs

**File**: `src/utils/definitions.py`

**Issue**: Database URL with password logged in plain text.

**Fix**: Mask password in log output via `_mask_password_in_url()`.

**Status**: [x] Already implemented

---

## Implementation Plan

### Phase 1: Quick Wins

- [x] Remove generic exception anti-patterns
- [x] Mask sensitive data in logs (already done)

### Phase 2: Infrastructure

- [x] Standardise session management with context managers
- [x] Add retry logic to HTTP clients

### Phase 3: Data Model

- [x] Fix currency precision (already done - uses `Numeric(12, 2)`)

---

## Testing Strategy

- [x] Unit tests for retry logic (3 new tests in `test_core.py`)
- [x] Unit tests for URL masking (already existed)
- [x] Verify no passwords appear in log output

---

## Changes Made

### Files Modified

1. `src/aws/ssm_parameters.py` - Removed generic exception handler
2. `src/postgres/gocardless/operations/bank_accounts.py` - Removed generic exception handler
3. `src/postgres/core.py` - Added connection pooling and `session_scope()` context manager
4. `src/providers/gocardless/api/core.py` - Added tenacity retry logic and `requests.Session`
5. `pyproject.toml` - Added `tenacity` dependency
6. `testing/providers/gocardless/api/test_core.py` - Updated tests for session mocking, added retry tests

---

## References

- Original PRD: `202601-backend-foundation-improvements.md` (split)
- Project standards: `backend/CLAUDE.md`
