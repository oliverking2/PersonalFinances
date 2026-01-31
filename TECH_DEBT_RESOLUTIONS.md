# Tech Debt Resolutions

Comprehensive list of technical debt identified in codebase review. Remove items you don't want to address, then work through remaining items.

---

## Critical Priority

### BE-001: N+1 Query in Accounts Endpoint

**File:** `backend/src/api/accounts/endpoints.py:56-59`

**Problem:**

```python
connections = get_connections_by_user_id(db, current_user.id)
accounts = []
for conn in connections:
    accounts.extend(get_accounts_by_connection_id(db, conn.id))  # N+1!
```

**Fix:** Add `selectinload(Connection.accounts)` to `get_connections_by_user_id()` or create dedicated `get_accounts_by_user_id()` operation.

**Impact:** O(N) extra queries per request. User with 5 connections = 6 DB calls instead of 1.

---

### BE-002: Duplicate _get_user_account_ids() Helper

**Files:**

- `backend/src/api/analytics/endpoints.py:59-67`
- `backend/src/api/transactions/endpoints.py:201-204`

**Problem:** Identical function defined in both files with same N+1 risk.

**Fix:** Move to shared module (e.g., `backend/src/api/common/helpers.py`) or create operation.

---

### BE-003: Missing Eager Loading in Transaction Queries

**File:** `backend/src/postgres/common/models.py:320-332`

**Problem:** All relationships use lazy loading:

```python
account: Mapped[Account] = relationship("Account")  # Lazy!
splits: Mapped[list["TransactionSplit"]] = relationship(...)  # Lazy!
pattern_links: Mapped[list["RecurringPatternTransaction"]] = relationship(...)  # Lazy!
```

When `_to_response()` accesses `transaction.splits[0].tag`, each triggers DB query.

**Fix:** Add `.options(selectinload(Transaction.splits).selectinload(TransactionSplit.tag))` to transaction queries in operations.

**Impact:** Could be 100+ queries per transaction list request.

---

### TEST-001: Missing API Endpoint Tests

**Missing test files for:**

| Endpoint Module  | File                             | Risk                              |
|------------------|----------------------------------|-----------------------------------|
| Notifications    | `api/notifications/endpoints.py` | Query features untested           |
| Tag Rules        | `api/tag_rules/endpoints.py`     | Complex rule engine (7 endpoints) |
| Trading212       | `api/trading212/endpoints.py`    | External broker integration       |

**Fix:** Create test files:

- `backend/testing/api/notifications/test_endpoints.py`
- `backend/testing/api/tag_rules/test_endpoints.py`
- `backend/testing/api/trading212/test_endpoints.py`

---

### DBT-001: Missing Schema Tests for Critical Models

**Files:**

- `backend/dbt/models/3_mart/fct_daily_balance_history.sql` - no column definitions
- `backend/dbt/models/3_mart/fct_cash_flow_forecast.sql` - no data tests

**Fix:** Add to `schema.yml`:

```yaml
- name: fct_daily_balance_history
  columns:
    - name: balance_date
      data_tests:
        - not_null
    - name: account_id
      data_tests:
        - not_null
        - relationships:
            to: ref('dim_accounts')
            field: account_id
```

---

## High Priority

### BE-004: Oversized sync.py File

**File:** `backend/src/postgres/common/operations/sync.py` (988 lines)

**Problem:** Mixes GoCardless and Trading212 sync logic with overlapping function names.

**Fix:** Split into:

- `backend/src/postgres/common/operations/sync_gocardless.py`
- `backend/src/postgres/common/operations/sync_trading212.py`

---

### BE-005: Repeated Account Ownership Verification

**Files:**

- `backend/src/api/accounts/endpoints.py:84-85, 108-109`
- `backend/src/api/transactions/endpoints.py:216-217, 240-245, 402-405, 443-445`
- `backend/src/api/goals/endpoints.py` (implicit)

**Problem:** Same verification pattern repeated:

```python
if account.connection.user_id != current_user.id:
    raise HTTPException(status_code=404, detail=f"Account not found: {account_id}")
```

**Fix:** Create shared helper:

```python
# backend/src/api/common/ownership.py
def verify_user_owns_account(db: Session, account_id: UUID, user: User) -> Account:
    account = get_account_by_id(db, account_id)
    if not account or account.connection.user_id != user.id:
        raise HTTPException(status_code=404, detail=f"Account not found: {account_id}")
    return account
```

---

### BE-006: _to_response() Coupling in Transactions

**File:** `backend/src/api/transactions/endpoints.py:127-198`

**Problem:** 70+ line function couples:

- Entity conversion
- Tag relationship navigation
- Recurring pattern logic
- Date formatting

**Fix:** Extract to dedicated converter module or use Pydantic's `model_validate()` with proper relationship loading.

---

### FE-001: parseFloat() Scattered Throughout (38 instances)

**Files:**

- `frontend/app/pages/planning/forecast.vue:80-97`
- `frontend/app/components/analytics/CashFlowForecastChart.vue:34, 47, 77, 80, 170-172`
- `frontend/app/components/analytics/ScenarioBuilder.vue:98-99`
- `frontend/app/pages/planning/net-worth.vue:189`
- `frontend/app/components/planning/PlannedTransactionsPanel.vue:113, 126, 214`
- `frontend/app/pages/settings/rules.vue:63, 73`

**Problem:** String-to-number conversion scattered, violates "Frontend handles formatting only".

**Fix:** Create utility:

```typescript
// frontend/app/utils/numbers.ts
export function parseDecimal(value: string | number): number {
  const num = typeof value === 'string' ? parseFloat(value) : value
  return isNaN(num) ? 0 : num
}
```

---

### FE-002: Duplicate Aggregation Logic

**Files:**

- `frontend/app/pages/index.vue:213-250`
- `frontend/app/pages/insights/analytics/index.vue:167-196`

**Problem:** Identical tag aggregation logic in both files. Violates CLAUDE.md: "All analytics logic belongs in dbt, not frontend".

**Fix:** Move to dbt model and query pre-aggregated data

---

### FE-003: Duplicate formatCurrency() Implementations

**Files:**

- `frontend/app/pages/index.vue:310-317`
- `frontend/app/pages/planning/forecast.vue:130-137`
- `frontend/app/components/analytics/CashFlowForecastChart.vue`
- Multiple other locations

**Fix:** Create shared utility:

```typescript
// frontend/app/utils/formatting.ts
export function formatCurrency(amount: number, currency = 'GBP'): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency,
  }).format(amount)
}
```

---

### DBT-002: Duplicate Frequency Matching Logic

**Files:**

- `backend/dbt/models/3_mart/fct_cash_flow_forecast.sql:85-112, 150-174`
- `backend/dbt/models/3_mart/fct_recurring_patterns.sql:89-106`

**Problem:** Same CASE statement for frequency-to-interval mapping in 3 places.

**Fix:** Extract to macro:

```sql
-- backend/dbt/macros/calculate_next_date.sql
{% macro calculate_next_date_by_frequency(last_date, frequency) %}
  CASE {{ frequency }}
    WHEN 'weekly' THEN {{ last_date }} + INTERVAL '7 days'
    WHEN 'fortnightly' THEN {{ last_date }} + INTERVAL '14 days'
    WHEN 'monthly' THEN {{ last_date }} + INTERVAL '1 month'
    WHEN 'quarterly' THEN {{ last_date }} + INTERVAL '3 months'
    WHEN 'annual' THEN {{ last_date }} + INTERVAL '1 year'
  END
{% endmacro %}
```

---

### DBT-003: Logic in Wrong Layer - Balance Normalization

**File:** `backend/dbt/models/3_mart/dim_accounts.sql:23-34`

**Problem:** Credit card balance normalization in mart layer:

```sql
CASE
    WHEN CATEGORY = 'credit_card' AND CREDIT_LIMIT IS NOT NULL AND BALANCE_AMOUNT > 0
        THEN GREATEST(0, CREDIT_LIMIT - BALANCE_AMOUNT)
    ...
END AS NORMALIZED_BALANCE
```

**Fix:**

1. Create staging model: `stg_unified_accounts.sql` with normalization
2. Have `dim_accounts` reference staging model
3. Ensures consistent balance across all downstream models

---

### TEST-003: Copy-Pasted Test Fixtures

**Files:**

- `backend/testing/api/accounts/test_endpoints.py:17-65`
- `backend/testing/api/transactions/test_endpoints.py:17-64`
- `backend/testing/api/analytics/test_endpoints.py:24-74`

**Problem:** `test_institution_in_db`, `test_connection_in_db`, `test_account_in_db` duplicated.

**Fix:** Move to shared conftest:

```python
# backend/testing/conftest.py (add to existing)
@pytest.fixture
def test_institution_in_db(db_session: Session) -> Institution:
    ...

@pytest.fixture
def test_connection_in_db(db_session: Session, test_user_in_db: User, test_institution_in_db: Institution) -> Connection:
    ...

@pytest.fixture
def test_account_in_db(db_session: Session, test_connection_in_db: Connection) -> Account:
    ...
```

---

### TEST-004: Untested Trading212 Operations

**File:** `backend/src/postgres/trading212/operations/history.py` (15% coverage)

**Untested functions:**

- `upsert_orders()`
- `upsert_dividends()`
- `upsert_transactions()`

**Fix:** Create `backend/testing/postgres/trading212/operations/test_history.py`

---

## Medium Priority

### FE-004: Massive Vue Components

**Files:**

| File                                                              | Lines   |
|-------------------------------------------------------------------|---------|
| `frontend/app/pages/settings/rules.vue`                           | 1,229   |
| `frontend/app/pages/transactions.vue`                             | 1,125   |
| `frontend/app/pages/index.vue`                                    | 1,083   |
| `frontend/app/components/transactions/TransactionDetailModal.vue` | 740     |
| `frontend/app/pages/settings/accounts.vue`                        | 663     |

**Fix:** Extract logic into composables, break into smaller components.

---

### FE-005: Silent Error Handling

**Files:**

- `frontend/app/pages/planning/forecast.vue:57-59`
- `frontend/app/pages/index.vue:449-454`
- `frontend/app/pages/settings/accounts.vue` (multiple)

**Problem:**

```typescript
fetchForecast().catch(() => null)  // Silent failure
```

**Fix:** Add proper error logging or user feedback:

```typescript
fetchForecast().catch((e) => {
  console.error('Failed to fetch forecast:', e)
  return null
})
```

---

### FE-006: Console.log in Production Code

**Files:**

- `frontend/app/pages/index.vue:457, 470, 478, 489`
- `frontend/app/pages/transactions.vue`
- `frontend/app/stores/auth.ts:110, 133, 161`
- `frontend/app/components/notifications/NotificationBell.vue`
- `frontend/app/pages/settings/accounts.vue`

**Fix:** Remove or replace with proper logging that can be disabled in production.

---

### FE-007: Type Safety Gaps

**File:** `frontend/app/composables/useAuthenticatedFetch.ts:50, 87-90`

**Problem:**

```typescript
body?: Record<string, any>  // Weak typing
const response = error.response as { ... }  // Type assertion
```

**Fix:** Create proper interfaces for request/response types per endpoint.

---

### DB-001: Missing CHECK Constraints

**Files:**

- `backend/alembic/versions/b07a1a168df0_add_planned_transactions_table.py:28`
- `backend/alembic/versions/d0021699d9f2_add_direction_to_recurring_patterns.py:26`
- `backend/alembic/versions/204b49cb0781_add_financial_milestones_table.py:30`

**Missing constraints:**

| Table                  | Column      | Constraint                                   |
|------------------------|-------------|----------------------------------------------|
| `planned_transactions` | `amount`    | `CHECK (amount != 0)`                        |
| `recurring_patterns`   | `direction` | `CHECK (direction IN ('expense', 'income'))` |
| `financial_milestones` | `colour`    | `CHECK (colour ~ '^#[0-9A-Fa-f]{6}$')`       |

**Fix:** Create migration to add constraints.

---

### DB-002: BalanceSnapshot Uses Integer PK

**Files:**

- `backend/alembic/versions/cdc71e9eb6d7_add_balance_snapshots_table.py:25`
- `backend/src/postgres/common/models.py:898`

**Problem:** Uses `Integer` autoincrement while all other tables use `UUID`.

**Fix:** Create migration to convert to UUID (breaking change, requires data migration).

---

### DB-003: Missing Composite Index

**File:** `backend/alembic/versions/b07a1a168df0_add_planned_transactions_table.py:42-43`

**Problem:** No index for frequent query pattern `(user_id, enabled)`.

**Fix:** Add migration:

```python
op.create_index(
    "idx_planned_transactions_user_enabled",
    "planned_transactions",
    ["user_id", "enabled"]
)
```

---

### DBT-004: Inefficient EXISTS Subquery

**File:** `backend/dbt/models/3_mart/fct_monthly_trends.sql:38-47`

**Problem:**

```sql
WHERE OUTGOING.AMOUNT < 0
AND EXISTS (
    SELECT 1 FROM TRANSACTIONS_WITH_USER AS INCOMING
    WHERE INCOMING.BOOKING_DATE = OUTGOING.BOOKING_DATE
    AND INCOMING.AMOUNT = -OUTGOING.AMOUNT
)
```

O(n²) complexity for internal transfer detection.

**Fix:** Use window function or self-join with explicit pairing.

---

### DBT-005: Inconsistent NULL Handling

**Files:**

- `backend/dbt/models/3_mart/fct_transactions.sql:64` - `COALESCE(AGG.TAGS, [])`
- `backend/dbt/models/3_mart/fct_daily_spending_by_tag.sql:189-191` - `'No Spending'` vs `'Untagged'`
- `backend/dbt/models/3_mart/fct_cash_flow_forecast.sql:217-220` - `COALESCE(..., 0)`

**Fix:** Document standard NULL handling strategy in CLAUDE.md and apply consistently.

---

### DBT-006: Missing Calculation Rationale Comments

**File:** `backend/dbt/models/3_mart/int_recurring_candidates.sql:137-145`

**Problem:** Magic numbers without explanation:

```sql
WHEN STS.AVG_INTERVAL BETWEEN 5 AND 10 THEN 'weekly'
WHEN STS.AVG_INTERVAL BETWEEN 12 AND 20 THEN 'fortnightly'
```

**Fix:** Add comments explaining why these ranges were chosen.

---

### TEST-005: Weak Test Assertions

**File:** `backend/testing/api/transactions/test_endpoints.py:262-285`

**Problem:**

```python
assert "id" in txn  # Only checks key exists, not value correctness
```

**Fix:** Assert actual values:

```python
assert txn["id"] == str(expected_transaction.id)
assert Decimal(txn["amount"]) == expected_transaction.amount
```

---

### TEST-006: Tests Coupled to Implementation

**File:** `backend/testing/api/analytics/test_endpoints.py:396-431`

**Problem:**

```python
mock_build.assert_called_once()
call_kwargs = mock_build.call_args.kwargs
assert call_kwargs["limit"] == 50
```

Tests internal function calls, not API behavior.

**Fix:** Test the actual response data reflects pagination, not that internal functions were called.

---

### TEST-007: Time-Dependent Tests

**File:** `backend/testing/api/analytics/test_forecasting.py:18-52`

**Problem:** Uses `date.today()` without freezing time.

**Fix:** Use `freezegun`:

```python
from freezegun import freeze_time

@freeze_time("2024-01-15")
def test_returns_forecast_data(self, ...):
    ...
```

---

## Low Priority

### BE-007: Inconsistent Session Parameter Naming

**Problem:** Operations use `session`, endpoints use `db` for same Session object.

**Fix:** Standardize to one name (recommend `session` per backend/CLAUDE.md).

---

### BE-008: Fragile Circular Import Pattern

**File:** `backend/src/postgres/common/models.py:20`

```python
from src.postgres.auth.models import User  # noqa: F401
```

**Problem:** Import only for SQLAlchemy FK resolution, fragile if removed.

**Fix:** Add explicit comment explaining why import is required.

---

### FE-008: Direct Array Index Assignment

**Files:**

- `frontend/app/pages/settings/accounts.vue:253`
- `frontend/app/pages/settings/tags.vue:169`
- `frontend/app/pages/settings/rules.vue:273`

**Problem:**

```typescript
connections.value[index] = updated
```

**Fix:** Use immutable update:

```typescript
connections.value = connections.value.map((c, i) => i === index ? updated : c)
```

---

### FE-009: TODO in Auth Store

**File:** `frontend/app/stores/auth.ts:15`

```typescript
first_name: string // TODO: Backend will add these fields
```

**Fix:** Resolve with backend or make fields optional.

---

### DB-005: Inconsistent Index Naming

**Problem:** Most use `idx_{table}_{columns}` but some abbreviate.

**Fix:** Audit and standardize all index names.

---

### DBT-007: Deep Model DAG

**Problem:** `fct_cash_flow_forecast` depends on `fct_net_worth_history` which depends on `fct_daily_balance_history`.

**Fix:** Consider intermediate checkpoint models to reduce coupling.

---

### TEST-008: Multi-Concern Tests

**File:** `backend/testing/api/analytics/test_forecasting.py:228-281`

**Problem:** Single test validates HTTP status, response structure, calculation correctness, and balance preservation.

**Fix:** Split into focused tests.

---

## Completed Items - Move items here as they are resolved

- [ ] Example: BE-001 - Fixed in PR #123

---

## Notes

- Run `make check` in affected directories after each fix
- Update CLAUDE.md if new patterns established
- Consider grouping related fixes into single PRs
