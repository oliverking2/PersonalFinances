# PRD: Smart Tagging

**Status**: Draft
**Author**: Claude
**Created**: 2026-01-25
**Updated**: 2026-01-25

---

## Overview

Smart Tagging introduces automated transaction categorisation through standard tags, rule-based auto-tagging, and transaction splitting. This foundation enables accurate budgeting by ensuring consistent categorisation across all transactions.

## Problem Statement

Currently, users must manually tag every transaction. This is:

1. **Time-consuming** - Users have hundreds of transactions per month
2. **Inconsistent** - Same merchants may be tagged differently over time
3. **Incomplete** - Many transactions remain untagged, skewing analytics
4. **Inflexible** - A single transaction can only have one category, but real purchases often span multiple categories (e.g., supermarket shop with groceries + household items)

## Goals

- Reduce manual tagging effort by 80%+ through auto-tagging rules
- Provide consistent categorisation across similar transactions
- Enable accurate per-category budgeting through transaction splits
- Maintain user control - all auto-tags can be overridden

## Non-Goals

- Machine learning / AI-based categorisation (future phase)
- Bank-provided category mapping (read-only, not editable)
- Recurring transaction detection (separate feature)
- Budget alerts or limits (separate feature)

---

## User Stories

1. **As a** new user, **I want** a sensible set of default tags available, **so that** I can start categorising immediately without setup
2. **As a** user, **I want** transactions from the same merchant to be auto-tagged consistently, **so that** I don't repeat the same tagging work
3. **As a** user, **I want to** create rules like "tag all Tesco transactions as Groceries", **so that** future transactions are categorised automatically
4. **As a** user, **I want to** split a supermarket purchase into Groceries and Household, **so that** my category spending is accurate
5. **As a** user, **I want to** see which tags were auto-assigned vs manually applied, **so that** I can review and correct if needed
6. **As a** user, **I want to** override auto-tags without affecting the rule, **so that** I can handle exceptions

---

## Proposed Solution

### High-Level Design

Three interconnected features:

1. **Standard Tags** - Pre-defined tags seeded on account creation, marked as system tags
2. **Auto-Tagging Rules** - User-defined rules that match transactions and apply tags automatically
3. **Split Transactions** - Ability to allocate a transaction's amount across multiple tags

### Data Model

#### 1. Tag Model Changes

```sql
-- Add to existing tags table
ALTER TABLE tags ADD COLUMN is_standard BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE tags ADD COLUMN is_hidden BOOLEAN NOT NULL DEFAULT FALSE;

-- Standard tags are seeded per-user, cannot be deleted (only hidden)
-- is_hidden allows users to "delete" standard tags from their view
```

#### 2. New: Tag Rules Table

```sql
CREATE TABLE tag_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    priority INTEGER NOT NULL DEFAULT 0,  -- Higher = evaluated first
    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    -- Conditions (all non-null conditions must match - AND logic)
    -- Include conditions (transaction must match)
    merchant_contains VARCHAR(256),       -- Case-insensitive contains
    merchant_exact VARCHAR(256),          -- Exact match (faster)
    description_contains VARCHAR(256),    -- Contains match on description
    min_amount DECIMAL(18,2),             -- Absolute value comparison
    max_amount DECIMAL(18,2),
    account_id UUID REFERENCES accounts(id) ON DELETE CASCADE,

    -- Exclude conditions (transaction must NOT match)
    merchant_not_contains VARCHAR(256),   -- Exclude if merchant contains this
    description_not_contains VARCHAR(256), -- Exclude if description contains this

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT uq_tag_rules_user_name UNIQUE (user_id, name)
);

CREATE INDEX idx_tag_rules_user_enabled ON tag_rules(user_id, enabled, priority DESC);
```

**Rule matching logic:**

1. All include conditions that are set must match (AND)
2. All exclude conditions that are set must NOT match (AND NOT)
3. Example: `merchant_contains = "Tesco"` AND `merchant_not_contains = "Petrol"` matches "Tesco Express" but not "Tesco Petrol Station"

#### 3. TransactionTag Changes

```sql
-- Add to existing transaction_tags table
ALTER TABLE transaction_tags ADD COLUMN is_auto BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE transaction_tags ADD COLUMN rule_id UUID REFERENCES tag_rules(id) ON DELETE SET NULL;

-- is_auto = TRUE means tag was applied by a rule
-- rule_id tracks which rule applied it (NULL if rule deleted or manual)
```

#### 4. New: Transaction Splits Table

```sql
CREATE TABLE transaction_splits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    amount DECIMAL(18,2) NOT NULL,  -- Absolute value, always positive
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT uq_transaction_splits UNIQUE (transaction_id, tag_id)
);

CREATE INDEX idx_transaction_splits_transaction ON transaction_splits(transaction_id);
CREATE INDEX idx_transaction_splits_tag ON transaction_splits(tag_id);

-- Constraint: Sum of splits must equal transaction amount (enforced in application)
```

#### 5. Transaction Note Field

```sql
-- Add to existing transactions table
ALTER TABLE transactions ADD COLUMN user_note VARCHAR(512);

-- Optional note added by user (useful for split context)
```

### API Endpoints

#### Standard Tags (minimal new endpoints)

| Method  | Path                    | Description                              |
|---------|-------------------------|------------------------------------------|
| -       | -                       | Standard tags use existing tag endpoints |
| PUT     | `/api/tags/{id}/hide`   | Hide a standard tag (soft delete)        |
| PUT     | `/api/tags/{id}/unhide` | Unhide a standard tag                    |

#### Tag Rules

| Method   | Path                       | Description                                     |
|----------|----------------------------|-------------------------------------------------|
| GET      | `/api/tag-rules`           | List all rules for user (ordered by priority)   |
| POST     | `/api/tag-rules`           | Create a new rule                               |
| GET      | `/api/tag-rules/{id}`      | Get rule details                                |
| PUT      | `/api/tag-rules/{id}`      | Update rule                                     |
| DELETE   | `/api/tag-rules/{id}`      | Delete rule                                     |
| POST     | `/api/tag-rules/{id}/test` | Test rule against recent transactions (preview) |
| POST     | `/api/tag-rules/reorder`   | Update priority ordering                        |
| POST     | `/api/tag-rules/apply`     | Re-apply all rules to untagged transactions     |

#### Transaction Splits

| Method   | Path                            | Description                         |
|----------|---------------------------------|-------------------------------------|
| GET      | `/api/transactions/{id}/splits` | Get splits for a transaction        |
| PUT      | `/api/transactions/{id}/splits` | Create/update splits (replaces all) |
| DELETE   | `/api/transactions/{id}/splits` | Remove all splits                   |

### UI/UX

#### 1. Tag Management (Settings > Tags)

- List shows standard vs custom tags with visual distinction
- Standard tags show "Standard" badge, cannot be deleted
- "Hide" option for standard tags user doesn't want
- "Show hidden" toggle to manage hidden standard tags

#### 2. Rules Management (Settings > Auto-Tagging Rules)

- List of rules with name, conditions summary, target tag, enabled toggle
- Drag-to-reorder for priority
- Create/edit rule modal:
  - Name field
  - Target tag selector
  - **Include conditions** (match these):
    - Merchant name (contains/exact match)
    - Description (contains)
    - Amount range (min/max)
    - Account selector
  - **Exclude conditions** (don't match these):
    - Merchant not contains
    - Description not contains
  - "Test rule" button showing matching transactions
  - Enable/disable toggle

#### 3. Transaction Detail Modal Updates

- Show "Auto-tagged" indicator on auto-applied tags
- "Split transaction" button when transaction has tags
- User note field (optional, saved on transaction)
- Split editor:
  - Shows transaction amount at top
  - List of splits: tag selector + amount/percentage
  - Slider UI for intuitive split allocation (drag to adjust percentages)
  - "Add split" button
  - Running total + remaining amount
  - Validation: splits must sum to transaction amount
  - Save/cancel buttons

#### 4. Transaction Row Updates

- Visual indicator for split transactions (e.g., stacked icon)
- Tooltip showing split breakdown on hover

---

## Technical Considerations

### Dependencies

- No new external libraries required
- Affects: Tag operations, Transaction operations, Analytics dbt models

### Migration

1. Add new columns to existing tables (nullable initially)
2. Seed standard tags for all existing users
3. Backfill `is_auto = FALSE` for existing transaction_tags
4. Update analytics dbt models to handle splits

### Performance

- Tag rules evaluated on transaction sync (Dagster job)
- Rules cached per-user during bulk operations
- Splits are denormalised in analytics for query performance
- Index on `tag_rules(user_id, enabled, priority)` for fast rule lookup

### Security

- All endpoints user-scoped (existing pattern)
- Rule patterns sanitised to prevent ReDoS
- Split amounts validated server-side (must sum to transaction amount)

### Analytics Impact

The `fct_daily_spending_by_tag` dbt model needs updates:

- When a transaction has splits, use split amounts instead of transaction amount
- Transactions without splits continue to use full amount
- Handle "No Spending" gap-fill rows (already implemented)

```sql
-- Pseudocode for split-aware aggregation
SELECT
    COALESCE(split.amount, ABS(txn.amount)) AS spending_amount,
    COALESCE(split.tag_id, txn_tag.tag_id) AS tag_id
FROM transactions txn
LEFT JOIN transaction_splits split ON txn.id = split.transaction_id
LEFT JOIN transaction_tags txn_tag ON txn.id = txn_tag.transaction_id
```

---

## Implementation Plan

### Phase 1: Standard Tags

- [ ] Add `is_standard` and `is_hidden` columns to Tag model
- [ ] Create migration
- [ ] Define standard tag set (constants)
- [ ] Seed standard tags on user registration
- [ ] Backfill standard tags for existing users (migration)
- [ ] Update tag deletion to prevent deleting standard tags
- [ ] Add hide/unhide endpoints
- [ ] Update frontend tag list with standard tag UI
- [ ] Tests

### Phase 2: Auto-Tagging Rules

- [ ] Create TagRule model and migration
- [ ] Add `is_auto` and `rule_id` to TransactionTag model
- [ ] Create tag rules CRUD endpoints
- [ ] Implement rule matching logic
- [ ] Add rule testing endpoint (preview matches)
- [ ] Integrate with transaction sync (Dagster)
- [ ] Create rules management UI
- [ ] Add auto-tag indicator to transaction display
- [ ] Tests

### Phase 3: Split Transactions

- [ ] Create TransactionSplit model and migration
- [ ] Create split CRUD endpoints
- [ ] Add split validation (amounts must sum)
- [ ] Update transaction detail modal with split UI
- [ ] Add split indicator to transaction rows
- [ ] Update analytics dbt models for splits
- [ ] Tests

---

## Testing Strategy

### Unit Tests

- [ ] Tag model: is_standard validation, hide/unhide logic
- [ ] TagRule model: condition matching, priority ordering
- [ ] TransactionSplit model: amount validation, sum constraint
- [ ] Rule matching engine: various condition combinations

### Integration Tests

- [ ] Standard tag seeding on user creation
- [ ] Rule application during transaction sync
- [ ] Split creation and analytics aggregation
- [ ] Rule priority ordering

### Manual Testing

- [ ] Create rules with various conditions
- [ ] Verify auto-tagging on new transactions
- [ ] Split a transaction and verify analytics
- [ ] Override auto-tag and verify rule doesn't reapply
- [ ] Hide/unhide standard tags

---

## Rollout Plan

1. **Development**: Implement in phases, feature-flagged if needed
2. **Testing**: Full test coverage before each phase
3. **Production**: Deploy phases sequentially
   - Phase 1 can deploy independently
   - Phase 2 requires Phase 1
   - Phase 3 can deploy independently

---

## Open Questions

- [x] Should standard tags be editable (name/colour)? **Decision: Yes, users can customise appearance**
- [x] Should auto-tags be re-evaluated when rules change? **Decision: No, only new transactions. Provide "re-apply" button**
- [x] Should splits support notes/descriptions? **Decision: Yes, one note on the transaction (not per-split)**
- [x] Maximum number of rules per user? **Decision: No limit**
- [x] Should rules support OR conditions or only AND? **Decision: AND only (simpler, create multiple rules for OR)**

---

## Standard Tags (Proposed Set)

| Name          | Colour  | Description                       |
|---------------|---------|-----------------------------------|
| Groceries     | #22c55e | Supermarkets, food shops          |
| Dining        | #f97316 | Restaurants, takeaways, cafes     |
| Transport     | #3b82f6 | Fuel, public transport, parking   |
| Utilities     | #8b5cf6 | Electric, gas, water, council tax |
| Entertainment | #ec4899 | Streaming, cinema, games          |
| Shopping      | #14b8a6 | General retail, online shopping   |
| Subscriptions | #6366f1 | Recurring services                |
| Health        | #ef4444 | Pharmacy, gym, medical            |
| Travel        | #0ea5e9 | Hotels, flights, holidays         |
| Income        | #10b981 | Salary, refunds, transfers in     |
| Transfers     | #6b7280 | Between own accounts              |
| Fees          | #f59e0b | Bank charges, interest            |

---

## References

- Current tag implementation: `backend/src/postgres/common/models.py`
- Transaction model: `backend/src/postgres/common/models.py`
- Analytics model: `backend/dbt/models/3_mart/fct_daily_spending_by_tag.sql`
