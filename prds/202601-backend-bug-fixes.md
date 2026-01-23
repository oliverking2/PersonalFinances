# PRD: Backend Critical Bug Fixes

**Status**: In Progress
**Author**: Claude
**Created**: 2026-01-17
**Updated**: 2026-01-23

---

## Overview

Fix critical bugs that cause crashes, data loss, or silent failures in the backend. These issues were identified during a comprehensive codebase review and must be resolved before adding new features.

## Problem Statement

The current codebase has several issues that prevent normal operation:

1. Requisition creation fails due to missing required field
2. HTTP requests can hang indefinitely without timeouts
3. Rate limits only handled on GET requests, not POST/PUT/DELETE
4. Environment variable access crashes instead of failing gracefully

## Goals

- Fix all critical bugs that cause crashes or data loss
- Ensure all network operations have timeouts
- Handle rate limits consistently across all HTTP methods

## Non-Goals

- Adding new features
- Performance optimisation
- Refactoring beyond what's needed for fixes

---

## Bugs to Fix

### 1. Missing `friendly_name` in Requisition Creation

**Files**: `src/postgres/gocardless/operations/requisitions.py`, `src/api/connections/endpoints.py`

**Issue**: Creating a new requisition link fails with database constraint violation because `friendly_name` is NOT NULL but not provided.

**Fix**: Add `friendly_name` parameter to `add_requisition_link()` and pass it from the API.

**Status**: [ ] Not started

### 2. Rate Limit Handling Missing on POST/PUT/DELETE

**File**: `src/providers/gocardless/api/core.py`

**Issue**: Only `make_get_request()` checks for 429 rate limit responses. POST, PUT, and DELETE requests will fail silently with rate limit errors.

**Fix**: Add rate limit checking to all HTTP methods in `GoCardlessCredentials`.

**Status**: [ ] Not started

### 3. Missing Timeouts on All HTTP Requests

**Files**: `src/providers/gocardless/api/core.py`, `src/aws/s3.py`

**Issue**: All `requests.*` calls and boto3 operations have no timeout configuration. Network issues will cause indefinite hangs.

**Fix**: Add `timeout=30` to all requests calls. Add `Config(connect_timeout=30, read_timeout=60)` to boto3 clients.

**Status**: [ ] Not started

### 4. Environment Variable Crash

**File**: `src/orchestration/gocardless/extraction/assets.py`

**Issue**: `os.environ["S3_BUCKET_NAME"]` crashes if env var missing instead of failing gracefully.

**Fix**: Use `os.getenv()` with validation or use Dagster resource configuration.

**Status**: [ ] Not started

---

## Implementation Plan

### Phase 1: Immediate Fixes

- [ ] Fix `friendly_name` in requisition creation
- [ ] Add rate limit checking to all HTTP methods
- [ ] Add timeouts to all network requests
- [ ] Fix environment variable handling in Dagster assets

---

## Testing Strategy

- [ ] Unit tests for rate limit handling
- [ ] Unit tests for timeout behaviour
- [ ] Manual test of requisition creation flow

---

## Success Metrics

- All critical bugs fixed and verified
- `make check` passes without errors
- No indefinite hangs on network operations

---

## References

- Original PRD: `202601-backend-foundation-improvements.md` (split)
