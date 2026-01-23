# PRD: Backend Code Quality Improvements

**Status**: In Progress
**Author**: Claude
**Created**: 2026-01-17
**Updated**: 2026-01-23

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

**Affected files**: Multiple files with `except Exception: raise` pattern

**Issue**: Catching and immediately re-raising adds no value and obscures stack traces.

**Fix**: Remove unnecessary try-except blocks or add meaningful error context.

**Status**: [ ] Not started

### 2. Standardise Database Session Management

**File**: `src/postgres/core.py`

**Issue**: Sessions created without cleanup, causing potential connection leaks.

**Fix**:

- Add context manager pattern for session lifecycle
- Configure connection pooling explicitly
- Use Dagster's resource pattern consistently

**Status**: [ ] Not started

### 3. Fix Currency Precision

**File**: `src/postgres/gocardless/models.py`

**Issue**: `balance_amount` uses `float` which causes precision loss for currency.

**Fix**: Use `Numeric` type with explicit precision for all money fields.

```python
from sqlalchemy import Numeric

balance_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
```

**Status**: [ ] Not started

### 4. Add Request Retry Logic

**File**: `src/providers/gocardless/api/core.py`

**Issue**: No retry logic for transient failures (network glitches, 5xx errors).

**Fix**: Implement exponential backoff with `tenacity` or `urllib3.Retry`.

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def make_get_request(self, url: str) -> dict:
    ...
```

**Status**: [ ] Not started

### 5. Mask Sensitive Data in Logs

**File**: `src/utils/definitions.py`

**Issue**: Database URL with password logged in plain text.

**Fix**: Mask password in log output or log URL without credentials.

```python
def mask_db_url(url: str) -> str:
    """Mask password in database URL for logging."""
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(url)
    if parsed.password:
        masked = parsed._replace(netloc=f"{parsed.username}:****@{parsed.hostname}:{parsed.port}")
        return urlunparse(masked)
    return url
```

**Status**: [ ] Not started

---

## Implementation Plan

### Phase 1: Quick Wins

- [ ] Remove generic exception anti-patterns
- [ ] Mask sensitive data in logs

### Phase 2: Infrastructure

- [ ] Standardise session management with context managers
- [ ] Add retry logic to HTTP clients

### Phase 3: Data Model

- [ ] Fix currency precision (requires migration)

---

## Testing Strategy

- [ ] Unit tests for retry logic
- [ ] Unit tests for URL masking
- [ ] Verify no passwords appear in log output

---

## Open Questions

- [ ] Should currency columns use `Decimal` or `Numeric` in SQLAlchemy? (Recommendation: `Numeric(19, 4)`)
- [ ] Should we add Pydantic models for GoCardless API responses now or defer?

---

## References

- Original PRD: `202601-backend-foundation-improvements.md` (split)
- Project standards: `backend/CLAUDE.md`
