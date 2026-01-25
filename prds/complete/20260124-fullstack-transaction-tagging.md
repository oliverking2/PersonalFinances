# PRD: Transaction Tagging

**Status**: In Progress
**Author**: Claude
**Created**: 2026-01-24
**Updated**: 2026-01-24

---

## Overview

Enable users to manually tag transactions with custom labels for personal categorisation, analytics, and budgeting. Tags are user-defined, flat (no hierarchy), and separate from the provider-supplied `category` field.

## Problem Statement

The current transaction model has a `category` field populated by bank providers (via GoCardless), but:

1. Provider categories are often generic or inconsistent across banks
2. Users cannot customise or override categorisation
3. No way to group transactions for budgeting (e.g., "Holiday 2026", "Home Renovation")
4. Analytics and reporting are limited to provider categories

Users need a flexible tagging system they control.

## Goals

- Allow users to create, edit, and delete custom tags
- Apply multiple tags to any transaction
- Bulk-tag transactions efficiently
- Filter transactions by tag
- Preserve provider `category` as read-only reference

## Non-Goals

- Hierarchical tag structure (folders, nested tags)
- Automatic/smart tagging based on rules (future feature)
- Tag suggestions based on merchant patterns (future feature)
- Budgeting/spending limits per tag (future feature)
- Sharing tags between users

---

## User Stories

1. **As a** user, **I want to** create custom tags like "Groceries" or "Subscriptions", **so that** I can categorise transactions my way
2. **As a** user, **I want to** apply multiple tags to a single transaction, **so that** I can track it across different contexts (e.g., "Food" + "Holiday")
3. **As a** user, **I want to** quickly tag multiple transactions at once, **so that** I can organise historical data efficiently
4. **As a** user, **I want to** filter my transaction list by tag, **so that** I can see spending in a specific category
5. **As a** user, **I want to** assign colours to tags, **so that** I can visually distinguish them in the UI

---

## Proposed Solution

### High-Level Design

Add a user-scoped tagging system with a many-to-many relationship to transactions. Tags are simple flat labels with optional colours. The existing `category` field remains untouched as provider data.

### Data Model

Two new tables: `tags` (user's tag definitions) and `transaction_tags` (junction table).

```sql
-- User-defined tags
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,
    colour VARCHAR(7),  -- Hex colour, e.g., "#10B981"
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, name)
);

CREATE INDEX idx_tags_user_id ON tags(user_id);

-- Many-to-many junction
CREATE TABLE transaction_tags (
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (transaction_id, tag_id)
);

CREATE INDEX idx_transaction_tags_tag_id ON transaction_tags(tag_id);
```

**Design decisions:**

| Decision             | Choice              | Rationale                                                                     |
|----------------------|---------------------|-------------------------------------------------------------------------------|
| Tag structure        | Flat (no hierarchy) | Simpler UX; users can encode hierarchy in names if needed ("Food: Groceries") |
| Seed tags            | None                | Users start fresh; avoids opinionated defaults                                |
| Tag limit            | 100 per user        | Soft limit; prevents abuse while allowing flexibility                         |
| Tags per transaction | 10 max              | Soft limit; encourages focused tagging                                        |
| Colour format        | Hex string          | Standard, easy to render in CSS                                               |

### API Endpoints

#### Tags CRUD

| Method   | Path             | Description                                |
|----------|------------------|--------------------------------------------|
| GET      | `/api/tags`      | List all tags for current user             |
| POST     | `/api/tags`      | Create a new tag                           |
| GET      | `/api/tags/{id}` | Get a specific tag                         |
| PUT      | `/api/tags/{id}` | Update tag name/colour                     |
| DELETE   | `/api/tags/{id}` | Delete tag (removes from all transactions) |

#### Transaction Tagging

| Method   | Path                                   | Description                 |
|----------|----------------------------------------|-----------------------------|
| POST     | `/api/transactions/{id}/tags`          | Add tag(s) to transaction   |
| DELETE   | `/api/transactions/{id}/tags/{tag_id}` | Remove tag from transaction |
| POST     | `/api/transactions/bulk/tags`          | Bulk add/remove tags        |

#### Query Extension

Update `GET /api/transactions` to accept `tag_id` query parameter for filtering.

### Request/Response Examples

**Create tag:**

```json
POST /api/tags
{
  "name": "Groceries",
  "colour": "#10B981"
}

Response: 201
{
  "id": "uuid",
  "name": "Groceries",
  "colour": "#10B981",
  "created_at": "2026-01-24T10:00:00Z"
}
```

**Add tags to transaction:**

```json
POST /api/transactions/{id}/tags
{
  "tag_ids": ["uuid1", "uuid2"]
}

Response: 200
{
  "transaction_id": "uuid",
  "tags": [
    {"id": "uuid1", "name": "Groceries", "colour": "#10B981"},
    {"id": "uuid2", "name": "Essentials", "colour": "#3B82F6"}
  ]
}
```

**Bulk tagging:**

```json
POST /api/transactions/bulk/tags
{
  "transaction_ids": ["uuid1", "uuid2", "uuid3"],
  "add_tag_ids": ["tag-uuid"],
  "remove_tag_ids": []
}

Response: 200
{
  "updated_count": 3
}
```

### UI/UX

#### Tags Management Page (`/settings/tags`)

- List all user tags with name, colour swatch, usage count
- Inline create: text input + colour picker + "Add" button
- Edit: click tag to open edit modal (name, colour, delete)
- Delete confirmation shows affected transaction count

#### Transaction List Enhancements

- Each row shows tag chips after amount/description
- Click chip area to open tag selector popover
- Tag selector: searchable list of tags, checkboxes for multi-select
- Quick-add: type new tag name directly in selector

#### Bulk Tagging

- Checkbox column on transaction rows
- Selection triggers toolbar: "X selected" + "Add Tags" button
- Tag selector modal for bulk operations

#### Tag Filtering

- Filter bar includes "Tags" dropdown (multi-select)
- Active tag filters shown as removable chips

---

## Technical Considerations

### Dependencies

**Backend:**

- No new external packages required
- Follows existing SQLAlchemy 2.0 patterns

**Frontend:**

- No new packages required
- Uses existing Headless UI components for popovers/modals

### Migration

- New tables only; no data migration required
- Alembic migration creates `tags` and `transaction_tags` tables
- Indexes included in migration

### Performance

- Junction table indexed on both foreign keys
- Tag count per user cached in listing query (not stored)
- Bulk operations use single INSERT with ON CONFLICT DO NOTHING
- Transaction list query: JOIN to fetch tags efficiently (limit 10 per transaction keeps payload small)

### Security

- Tags scoped to `user_id`; all queries filter by authenticated user
- Tag names sanitised (max 50 chars, stripped whitespace)
- Colour validated as hex format
- Transaction tagging validates transaction belongs to user's accounts
- Rate limiting on bulk operations (if needed)

---

## Implementation Plan

### Phase 1: Backend - Tag CRUD

- [ ] Add `Tag` and `TransactionTag` models to `models.py`
- [ ] Create Alembic migration
- [ ] Create `backend/src/postgres/common/operations/tags.py`
- [ ] Create `backend/src/api/tags/` router with CRUD endpoints
- [ ] Add tests for tag operations

### Phase 2: Backend - Transaction Tagging

- [ ] Add tagging endpoints to transactions router
- [ ] Add `tag_id` filter to transaction list query
- [ ] Update transaction response model to include tags
- [ ] Add tests for transaction tagging

### Phase 3: Frontend - Tags Management

- [ ] Create `frontend/app/types/tags.ts`
- [ ] Create `frontend/app/composables/useTagsApi.ts`
- [ ] Create `frontend/app/pages/settings/tags.vue`
- [ ] Add Tags link to settings navigation

### Phase 4: Frontend - Transaction Tagging

- [ ] Create `frontend/app/components/tags/TagChip.vue`
- [ ] Create `frontend/app/components/tags/TagSelector.vue`
- [ ] Update transaction row to show tags
- [ ] Add tag selector popover to transactions
- [ ] Add bulk selection and tagging UI

### Phase 5: Frontend - Filtering

- [ ] Add tag filter to transaction list filters
- [ ] Update `useTransactionsApi` to include tag filter param

---

## Testing Strategy

**Backend:**

- [ ] Unit tests: tag CRUD operations
- [ ] Unit tests: transaction tagging operations
- [ ] Integration tests: tag API endpoints
- [ ] Integration tests: transaction tagging endpoints
- [ ] Test user isolation (user A cannot see/use user B's tags)

**Frontend:**

- [ ] Component tests: TagChip, TagSelector
- [ ] E2E: create tag, apply to transaction, filter by tag

---

## Rollout Plan

1. **Development**: Implement all phases, local testing
2. **Validation**: Run `make check` in backend and frontend
3. **Production**: Deploy migration first, then application code

---

## Open Questions

All resolved during planning:

- [x] ~~Hierarchical tags?~~ No - flat structure, simpler UX
- [x] ~~Seed/default tags?~~ No - users start fresh
- [x] ~~Tag limits?~~ 100 per user, 10 per transaction (soft limits)

---

## Future Enhancements

These are explicitly out of scope but noted for future consideration:

1. **Auto-tagging rules**: "Tag all transactions from 'Tesco' as 'Groceries'"
2. **Smart suggestions**: ML-based tag recommendations
3. **Tag budgets**: Set spending limits per tag
4. **Tag analytics**: Charts/reports by tag over time
5. **Tag import/export**: Bulk management via CSV

---

## Files to Create/Modify

| Location                                                  | Action  | Description                        |
|-----------------------------------------------------------|---------|------------------------------------|
| `backend/src/postgres/common/models.py`                   | Modify  | Add `Tag`, `TransactionTag` models |
| `backend/alembic/versions/xxx_add_tags.py`                | Create  | Migration for new tables           |
| `backend/src/postgres/common/operations/tags.py`          | Create  | Tag CRUD operations                |
| `backend/src/api/tags/__init__.py`                        | Create  | Router module                      |
| `backend/src/api/tags/endpoints.py`                       | Create  | Tag API endpoints                  |
| `backend/src/api/tags/models.py`                          | Create  | Pydantic request/response models   |
| `backend/src/api/transactions/endpoints.py`               | Modify  | Add tagging endpoints, tag filter  |
| `backend/src/api/transactions/models.py`                  | Modify  | Add tags to response model         |
| `backend/testing/api/test_tags.py`                        | Create  | API tests                          |
| `backend/testing/postgres/operations/test_tags.py`        | Create  | Operation tests                    |
| `frontend/app/types/tags.ts`                              | Create  | Tag interfaces                     |
| `frontend/app/composables/useTagsApi.ts`                  | Create  | API composable                     |
| `frontend/app/pages/settings/tags.vue`                    | Create  | Tags management page               |
| `frontend/app/components/tags/TagChip.vue`                | Create  | Tag display component              |
| `frontend/app/components/tags/TagSelector.vue`            | Create  | Tag selection component            |
| `frontend/app/components/transactions/TransactionRow.vue` | Modify  | Show tags, add selector            |

---

## References

- Existing patterns: `backend/src/api/accounts/` for CRUD structure
- Existing patterns: `frontend/app/composables/useAccountsApi.ts` for API composable
- Transaction model: `backend/src/postgres/common/models.py:Transaction`
