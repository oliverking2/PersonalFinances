# PRD: Foundation Improvements & Test Suite

**Status**: Approved
**Author**: Claude
**Created**: 2026-01-16
**Updated**: 2026-01-16

---

## Overview

This PRD addresses critical bugs, code quality issues, and missing test coverage identified during a comprehensive codebase review. The goal is to stabilise the foundation before adding new features.

## Problem Statement

The current codebase has several issues that could cause data loss, silent failures, or crashes:

1. **Critical bugs** that prevent requisition creation and dbt model execution
2. **No test coverage** despite an 80% coverage requirement in project standards
3. **Missing error handling** with network requests that can hang indefinitely
4. **Inconsistent patterns** making the codebase harder to maintain

## Goals

- Fix all critical bugs that cause crashes or data loss
- Achieve 80% test coverage across the codebase
- Standardise error handling and HTTP client patterns
- Improve observability with consistent logging

## Non-Goals

- Adding new features (covered in separate PRDs)
- CI/CD pipeline (out of scope for personal app)
- Performance optimisation (defer until needed)

---

## Critical Bugs to Fix

### 1. Missing `friendly_name` in Requisition Creation

**Files**: `src/postgres/gocardless/operations/requisitions.py:73`, `src/streamlit/pages/connections.py:106`

**Issue**: Creating a new requisition link fails with database constraint violation because `friendly_name` is NOT NULL but not provided.

**Fix**: Add `friendly_name` parameter to `add_requisition_link()` and pass it from the Streamlit UI.

### 2. dbt Model Runtime Error

**File**: `dbt/models/1_source/src_gocardless_transactions.sql`

**Issue**: Model fails with "Binder Error: Referenced column '_extract_dt' not found in FROM clause"

**Fix**: Update the SQL to correctly reference columns available from `READ_JSON()` or remove the column if not needed.

### 3. Rate Limit Handling Missing on POST/PUT/DELETE

**File**: `src/gocardless/api/core.py:138-162`

**Issue**: Only `make_get_request()` checks for 429 rate limit responses. POST, PUT, and DELETE requests will fail silently with rate limit errors.

**Fix**: Add rate limit checking to all HTTP methods in `GoCardlessCredentials`.

### 4. Missing Timeouts on All HTTP Requests

**Files**: `src/gocardless/api/core.py`, `src/aws/s3.py`

**Issue**: All `requests.*` calls and boto3 operations have no timeout configuration. Network issues will cause indefinite hangs.

**Fix**: Add `timeout=30` to all requests calls. Add `Config(connect_timeout=30, read_timeout=60)` to boto3 clients.

### 5. Environment Variable Crash

**File**: `src/dagster/gocardless/extraction/assets.py:81,125`

**Issue**: `os.environ["S3_BUCKET_NAME"]` crashes if env var missing instead of failing gracefully.

**Fix**: Use `os.getenv()` with validation or use Dagster resource configuration.

---

## Code Quality Improvements

### 1. Remove Generic Exception Anti-patterns

**Affected files**: 10+ files with `except Exception: raise` pattern

**Issue**: Catching and immediately re-raising adds no value and obscures stack traces.

**Fix**: Remove unnecessary try-except blocks or add meaningful error context.

### 2. Standardise Database Session Management

**File**: `src/postgres/utils.py`

**Issue**: `create_session()` creates engine and session without cleanup, causing connection leaks.

**Fix**:
- Add context manager pattern for session lifecycle
- Configure connection pooling explicitly
- Use Dagster's `PostgresDatabase` resource pattern consistently

### 3. Fix Currency Precision

**File**: `src/postgres/gocardless/models.py:106`

**Issue**: `balance_amount` uses `float` which causes precision loss for currency.

**Fix**: Use `Decimal` type with explicit precision for all money fields.

### 4. Add Request Retry Logic

**File**: `src/gocardless/api/core.py`

**Issue**: No retry logic for transient failures.

**Fix**: Implement exponential backoff for token refresh and API calls.

### 5. Mask Sensitive Data in Logs

**File**: `src/utils/definitions.py:50,64`

**Issue**: Database URL with password logged in plain text.

**Fix**: Mask password in log output or log URL without credentials.

---

## Test Suite Implementation

### Test Infrastructure Setup

Create `testing/` directory structure mirroring `src/`:

```
testing/
├── __init__.py
├── conftest.py              # Shared fixtures
├── aws/
│   ├── __init__.py
│   ├── test_s3.py
│   └── test_ssm_parameters.py
├── gocardless/
│   ├── __init__.py
│   └── api/
│       ├── __init__.py
│       ├── test_core.py
│       ├── test_account.py
│       ├── test_requisition.py
│       └── test_institutions.py
├── postgres/
│   ├── __init__.py
│   └── gocardless/
│       ├── __init__.py
│       └── operations/
│           ├── __init__.py
│           ├── test_agreements.py
│           ├── test_bank_accounts.py
│           └── test_requisitions.py
├── dagster/
│   ├── __init__.py
│   └── gocardless/
│       ├── __init__.py
│       └── extraction/
│           ├── __init__.py
│           └── test_assets.py
└── utils/
    ├── __init__.py
    ├── test_definitions.py
    └── test_logging.py
```

### Shared Fixtures (conftest.py)

```python
# testing/conftest.py
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def mock_session():
    """In-memory SQLite session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    # Create tables...
    session = Session()
    yield session
    session.close()

@pytest.fixture
def mock_gocardless_credentials():
    """Mock GoCardless credentials."""
    with patch("src.gocardless.api.core.GoCardlessCredentials") as mock:
        instance = mock.return_value
        instance.make_get_request.return_value = {}
        instance.make_post_request.return_value = {}
        yield instance

@pytest.fixture
def mock_s3_client():
    """Mock boto3 S3 client."""
    with patch("boto3.client") as mock:
        yield mock.return_value
```

### Test Cases by Module

#### AWS Module Tests (15 test cases)

**test_s3.py**:
- `test_upload_file_success` - Verify file uploads correctly
- `test_upload_file_missing_bucket` - Handle missing bucket gracefully
- `test_upload_file_timeout` - Verify timeout behaviour
- `test_download_file_success` - Verify file downloads correctly
- `test_download_file_not_found` - Handle missing file gracefully
- `test_download_file_permission_denied` - Handle access denied
- `test_get_parquet_as_dataframe_success` - Read parquet correctly
- `test_get_parquet_as_dataframe_malformed` - Handle corrupt files
- `test_get_csv_from_s3_success` - Read CSV correctly
- `test_get_csv_from_s3_malformed` - Handle malformed CSV

**test_ssm_parameters.py**:
- `test_get_parameter_success` - Retrieve parameter correctly
- `test_get_parameter_not_found` - Handle missing parameter
- `test_get_parameter_access_denied` - Handle permission errors
- `test_get_parameter_decryption_failure` - Handle KMS errors
- `test_get_parameter_timeout` - Verify timeout behaviour

#### GoCardless API Tests (25 test cases)

**test_core.py**:
- `test_get_access_token_success` - Token retrieved correctly
- `test_get_access_token_refresh` - Token refreshes when expired
- `test_get_access_token_failure` - Handle auth failure
- `test_get_access_token_timeout` - Handle timeout
- `test_make_get_request_success` - GET returns data
- `test_make_get_request_rate_limit` - Rate limit raises exception
- `test_make_get_request_timeout` - Timeout raises exception
- `test_make_post_request_success` - POST returns data
- `test_make_post_request_rate_limit` - Rate limit raises exception
- `test_make_put_request_success` - PUT returns data
- `test_make_delete_request_success` - DELETE succeeds
- `test_make_delete_request_rate_limit` - Rate limit raises exception

**test_account.py**:
- `test_get_account_metadata_success` - Metadata returned
- `test_get_account_metadata_not_found` - Handle missing account
- `test_get_account_transactions_success` - Transactions returned
- `test_get_account_transactions_invalid_dates` - Handle bad date range
- `test_get_account_balances_success` - Balances returned

**test_requisition.py**:
- `test_create_requisition_link_success` - Link created
- `test_get_all_requisition_data_success` - All requisitions returned
- `test_get_requisition_data_success` - Single requisition returned
- `test_delete_requisition_success` - Requisition deleted

**test_institutions.py**:
- `test_get_all_institutions_success` - Institutions returned
- `test_get_institution_mapping_success` - Mapping built correctly

#### PostgreSQL Operations Tests (25 test cases)

**test_agreements.py**:
- `test_add_or_update_agreement_new` - New agreement added
- `test_add_or_update_agreement_existing` - Existing agreement updated
- `test_upsert_agreement_success` - Upsert works correctly

**test_bank_accounts.py**:
- `test_upsert_bank_accounts_new` - New accounts added
- `test_upsert_bank_accounts_existing` - Existing accounts updated
- `test_update_account_from_api_success` - Account metadata updated
- `test_get_active_accounts_success` - Active accounts returned
- `test_get_active_accounts_empty` - Empty list when none active
- `test_get_transaction_watermark_exists` - Watermark returned
- `test_get_transaction_watermark_none` - None when no watermark
- `test_update_transaction_watermark_success` - Watermark updated

**test_requisitions.py**:
- `test_add_requisition_link_success` - Link added with friendly_name
- `test_add_requisition_link_missing_friendly_name` - Error when missing
- `test_get_all_active_requisition_ids` - Active IDs returned
- `test_get_active_requisition_link` - Link returned by ID
- `test_get_active_requisitions` - All active links returned
- `test_upsert_requisition_status_new` - New requisition created
- `test_upsert_requisition_status_existing` - Status updated
- `test_update_requisition_link_to_expired` - Link marked expired

#### Dagster Asset Tests (12 test cases)

**test_assets.py**:
- `test_extract_transactions_success` - Transactions extracted to S3
- `test_extract_transactions_rate_limit` - Rate limit handled gracefully
- `test_extract_transactions_no_accounts` - Empty when no accounts
- `test_extract_account_details_success` - Details extracted
- `test_extract_account_balances_success` - Balances extracted
- `test_extract_missing_s3_bucket` - Graceful error on missing config
- `test_watermark_update_on_success` - Watermark updated after extraction
- `test_watermark_not_updated_on_failure` - Watermark preserved on failure

#### Utils Tests (8 test cases)

**test_definitions.py**:
- `test_get_host_local` - Returns localhost for local env
- `test_get_host_remote` - Returns configured host for remote
- `test_dagster_database_url_success` - URL built correctly
- `test_gocardless_database_url_success` - URL built correctly
- `test_database_url_missing_env_vars` - Error on missing config

**test_logging.py**:
- `test_get_logger_returns_dagster_logger` - Logger returned
- `test_logger_propagation` - Log messages propagate correctly

---

## dbt Improvements

### Fix Broken Model

**File**: `dbt/models/1_source/src_gocardless_transactions.sql`

Remove or fix the `_extract_dt` column reference that doesn't exist in the JSON source.

### Add Missing Tests

**File**: `dbt/models/2_staging/schema.yml`

Add comprehensive tests:

```yaml
models:
  - name: stg_gocardless_all_transactions
    columns:
      - name: transaction_id
        data_tests:
          - not_null
          - unique
      - name: account_id
        data_tests:
          - not_null
      - name: amount
        data_tests:
          - not_null
      - name: currency
        data_tests:
          - not_null
          - accepted_values:
              values: ['GBP', 'EUR', 'USD']
      - name: transaction_type
        data_tests:
          - not_null
          - accepted_values:
              values: ['booked', 'pending']
```

### Add Source Freshness

**File**: `dbt/models/1_source/schema.yml`

```yaml
sources:
  - name: dagster
    freshness:
      warn_after: {count: 24, period: hour}
      error_after: {count: 48, period: hour}
    loaded_at_field: _extract_dt
    tables:
      - name: gocardless_raw_transactions
        description: Raw transaction data from GoCardless API
      - name: gocardless_raw_account_details
        description: Account metadata from GoCardless API
      - name: gocardless_raw_account_balances
        description: Balance snapshots from GoCardless API
```

---

## Implementation Plan

### Phase 1: Critical Bug Fixes (Immediate)

- [ ] Fix `friendly_name` in requisition creation
- [ ] Fix dbt `src_gocardless_transactions.sql` error
- [ ] Add rate limit checking to all HTTP methods
- [ ] Add timeouts to all network requests
- [ ] Fix environment variable handling in Dagster assets

### Phase 2: Test Infrastructure (High Priority)

- [ ] Create `testing/` directory structure
- [ ] Add `conftest.py` with shared fixtures
- [ ] Implement AWS module tests (15 tests)
- [ ] Implement GoCardless API tests (25 tests)
- [ ] Implement PostgreSQL operations tests (25 tests)
- [ ] Implement Dagster asset tests (12 tests)
- [ ] Implement Utils tests (8 tests)

### Phase 3: Code Quality (High Priority)

- [ ] Remove generic exception anti-patterns
- [ ] Standardise session management with context managers
- [ ] Fix currency precision (float → Decimal)
- [ ] Add retry logic to HTTP clients
- [ ] Mask sensitive data in logs

### Phase 4: dbt Improvements (Medium Priority)

- [ ] Add comprehensive tests to staging models
- [ ] Add source freshness checks
- [ ] Add model and column documentation

---

## Testing Strategy

- [ ] Unit tests for all modules using mocks
- [ ] Integration tests for database operations using SQLite in-memory
- [ ] dbt tests for data quality validation
- [ ] Run `make coverage` and verify 80% threshold met

---

## Rollout Plan

1. **Development**: Fix bugs and add tests locally
2. **Validation**: Run `make check` to verify all tests pass
3. **Verification**: Manual testing of Streamlit UI and Dagster jobs

---

## Success Metrics

- All critical bugs fixed and verified
- `make coverage` reports 80%+ coverage
- `make check` passes without errors
- dbt models build without errors
- No indefinite hangs on network operations

---

## Open Questions

- [x] ~~Should we add CI/CD?~~ No, out of scope for personal app
- [ ] Should currency columns use `Decimal` or `Numeric` in SQLAlchemy?
- [ ] Should we add Pydantic models for GoCardless API responses now or defer?

---

## References

- Project standards: `CLAUDE.md`
- Roadmap: `ROADMAP.md`
- Code review findings (internal analysis)
